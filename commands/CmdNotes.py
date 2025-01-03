from evennia import default_cmds
from evennia.utils import evtable
from evennia.utils.utils import make_iter
from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.utils import crop
from evennia.utils.ansi import ANSIString
from world.wod20th.utils.ansi_utils import wrap_ansi
from world.wod20th.utils.formatting import header, footer, divider, format_stat
from collections import defaultdict
from django.utils import timezone
from evennia import logger
from evennia import search_object
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime

class CmdNotes(MuxCommand):
    """
    Manage character notes.

    Usage:
      +notes                      - see all your notes
      +note <note name or number> - see your note
      +note/<category>            - see all your notes in a category
      +note/decompile <note(s)>   - get the raw text that created the note
      +note <target>/*            - see all visible notes on someone else
      +note <target>/<note>       - see a note on someone else
      +note <target>/<category> - see all notes on someone else in a category
      +note/create <name>=<text>  - make a note called <name>
      +note/create <category>/<name>=<text> - make a note in a specific category
      +note/edit <note>=<new text> - change the text on a note, removes approval
      +note/move <note>=<category> - move a note to a new category, keeps approval
      +note/status <note>=PRIVATE|PUBLIC - make a note in-/visible to others
      +note/private <note>        - shortcut to make a note private
      +note/public <note>         - shortcut to make a note public
      +note/prove <note>=<target(s)> - show any note to a list of targets
      +note/approve[/<category>] <target>/<note> - approve a note (staff only)
      +note/unapprove[/<category>] <target>/<note> - unapprove a note (staff only)

      Sample categories: General, Story, Merit, Flaw, Rote, Magick, NPC, Background
      Combo Discipline, Ritual (use for Sabbat or Shifter)
    """

    key = "+note"
    aliases = ["+notes"]
    locks = "cmd:all()"
    help_category = "Character"

    def search_for_character(self, search_string):
        # First, try to find by exact name match
        results = search_object(search_string, typeclass="typeclasses.characters.Character")
        if results:
            return results[0]
        
        # If not found, try to find by dbref
        if search_string.startswith("#") and search_string[1:].isdigit():
            results = search_object(search_string, typeclass="typeclasses.characters.Character")
            if results:
                return results[0]
        
        # If still not found, return None
        return None

    def func(self):
        if not self.args and not self.switches:
            self.list_notes()
            return

        if self.switches:
            switch = self.switches[0].lower()
            if switch == "create":
                self.create_note()
            elif switch == "edit":
                self.edit_note()
            elif switch == "status":
                self.change_note_status()
            elif switch == "decompile":
                self.decompile_note()
            elif switch == "move":
                self.move_note()
            elif switch == "private":
                self.args = f"{self.args}=PRIVATE"
                self.change_note_status()
            elif switch == "public":
                self.args = f"{self.args}=PUBLIC"
                self.change_note_status()
            elif switch == "prove":
                self.prove_note()
            elif switch == "approve":
                self.approve_note()
            elif switch == "unapprove":
                self.unapprove_note()
            else:
                self.caller.msg(f"Unknown switch: {switch}")
        else:
            # View a specific note
            self.view_note()

    def list_notes(self):
        notes = self.caller.get_all_notes()
        if not notes:
            self.caller.msg("You don't have any notes.")
            return

        width = 78
        notes_by_category = defaultdict(list)
        for note in notes:
            notes_by_category[note.category].append(note)

        output = header(f"Notes for {self.caller.name}", width=width, color="|y", fillchar="|r=|n", bcolor="|b")

        for category, category_notes in notes_by_category.items():
            # Category header in white
            output += f"|w{category}|n ({len(category_notes)})\n"
            
            for note in category_notes:
                # Note header with ID
                output += f"* #{note.note_id} {note.name}"
                
                # Add status if private/pending
                if hasattr(note, 'is_public') and not note.is_public:
                    output += " (PRIVATE"
                    if not note.is_approved:
                        output += ", PENDING"
                    output += ")"
                output += "\n"
                
                # Note text indented
                text_lines = note.text.split('\n')
                for line in text_lines:
                    output += "    " + line + "\n"

        output += footer(width=width, fillchar="|r=|n")
        
        self.caller.msg(output)

    def create_note(self):
        """Create a new note."""
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: +note/create <name>=<text>")
            return

        name, text = self.args.split("=", 1)
        name = name.strip()
        text = text.strip()

        # Handle category in name
        if "/" in name:
            category, name = name.split("/", 1)
            category = category.strip().title()
        else:
            category = "General"

        try:
            note = self.caller.add_note(name, text, category=category)
            self.caller.msg(f"Created note #{note.note_id}: {note.name}")
        except Exception as e:
            self.caller.msg(f"Error creating note: {e}")

    def edit_note(self):
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: +note/edit <note>=<new text>")
            return

        note_id, text = self.args.split("=", 1)
        note_id = note_id.strip()
        text = text.strip()

        if self.caller.update_note(note_id, text=text):
            self.caller.msg(f"Note '{note_id}' updated.")
        else:
            self.caller.msg(f"Note '{note_id}' not found.")

    def view_note(self):
        """View a specific note."""
        if not self.args:
            self.list_notes()
            return

        if "/" in self.args:
            target_name, note_id = self.args.split("/", 1)
            target = self.search_for_character(target_name)
            if not target:
                return
            
            # Handle wildcard to show all notes
            if note_id == "*":
                self.list_character_notes(target)
                return
        else:
            target = self.caller
            note_id = self.args

        # Only proceed if not wildcard
        note = target.get_note(note_id)
        if not note:
            self.caller.msg("No note with that ID exists.")
            return

        # Check permissions
        if target != self.caller and not (note.is_public or self.caller.check_permstring("Builders")):
            self.caller.msg("You don't have permission to view this note.")
            return

        self.display_note(note)

    def list_character_notes(self, target):
        """List all viewable notes for a character."""
        notes = target.get_all_notes()
        if not notes:
            self.caller.msg(f"{target.name} has no notes.")
            return

        width = 78
        notes_by_category = defaultdict(list)
        for note in notes:
            # Only show public notes or if viewer is staff
            if note.is_public or self.caller.check_permstring("Builders") or target == self.caller:
                notes_by_category[note.category].append(note)

        if not any(notes_by_category.values()):
            self.caller.msg(f"No viewable notes found for {target.name}.")
            return

        output = header(f"Notes for {target.name}", width=width, fillchar="|r=|n")

        for category, category_notes in notes_by_category.items():
            if category_notes:  # Only show categories that have viewable notes
                # Just show the category name in cyan, similar to list_notes()
                output += f"|w{category}|n (#" + str(len(category_notes)) + ")\n"
                
                for note in category_notes:
                    truncated_text = note.text[:60] + "..." if len(note.text) > 60 else note.text
                    wrapped_text = wrap_ansi(truncated_text, width=width-4)
                    
                    visibility = "|gPUBLIC|n" if note.is_public else "|rPRIVATE|n"
                    approved = "|gAPPROVED|n" if note.is_approved else "|rPENDING|n"
                    note_header = f"|y* |w#{note.note_id}|n {note.name} ({visibility}, {approved})"
                    output += note_header + "\n"
                    output += "    " + wrapped_text.replace("\n", "\n    ") + "\n\n"

        output += footer(width=width, fillchar="|r=|n")
        self.caller.msg(output)

    def list_notes_by_category(self, category):
        """List all notes in a specific category."""
        notes = self.caller.get_all_notes()
        if not notes:
            self.caller.msg("You don't have any notes.")
            return

        category_notes = [note for note in notes if note.category.lower() == category.lower()]
        if not category_notes:
            self.caller.msg(f"No notes found in category '{category}'.")
            return

        width = 78
        output = header(f"Notes in category '{category}'", width=width, fillchar="|r=|n")
        
        for note in category_notes:
            truncated_text = note.text[:60] + "..." if len(note.text) > 60 else note.text
            wrapped_text = wrap_ansi(truncated_text, width=width-4)
            
            note_header = f"|y* |w#{note.note_id} |n{note.name}"
            output += note_header + "\n"
            output += "    " + wrapped_text.replace("\n", "\n    ") + "\n\n"

        output += footer(width=width, fillchar="|r=|n")
        self.caller.msg(output)

    def list_room_characters(self):
        """List all characters in the current room."""
        if not self.caller.location:
            self.caller.msg("You are not in any location.")
            return
        
        characters = [obj for obj in self.caller.location.contents 
                     if obj.has_account and obj != self.caller]
        
        if not characters:
            self.caller.msg("No other characters found in this location.")
            return

        self.caller.msg("Characters in this location:")
        for char in characters:
            self.caller.msg(f"- {char.name}")

    def decompile_note(self):
        """Get the raw text of a note."""
        if not self.args:
            self.caller.msg("Usage: +note/decompile <note>")
            return

        if "/" in self.args:
            target_name, note_id = self.args.split("/", 1)
            target = self.search_for_character(target_name)
            if not target:
                return
        else:
            target = self.caller
            note_id = self.args

        note = target.get_note(note_id)
        if not note:
            self.caller.msg("No note with that ID exists.")
            return

        # Check permissions
        if target != self.caller and not self.caller.check_permstring("Builders"):
            self.caller.msg("You don't have permission to decompile this note.")
            return

        # Format the decompiled output
        output = f"+note/create {note.category}/{note.name}={note.text}"
        if note.is_public:
            output += "\n+note/public #{note.note_id}"
        self.caller.msg(output)

    def move_note(self):
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: +note/move <note name>=<new category>")
            return

        note_name, new_category = self.args.split("=", 1)
        note_name = note_name.strip()
        new_category = new_category.strip()

        note = self.caller.get_note(note_name)
        if not note:
            self.caller.msg(f"Note not found: {note_name}")
            return

        self.caller.update_note(note_name, note.text, new_category)
        self.caller.msg(f"Note '{note_name}' moved to category '{new_category}'.")

    def change_note_status(self):
        if not self.args or "=" not in self.args:
            # Check if it's a direct public/private command without =
            if "/" in self.args:
                target_name, note_id = self.args.split("/", 1)
                target = self.search_for_character(target_name)
                if not target:
                    return
            else:
                target = self.caller
                note_id = self.args

            # Set status based on the switch used
            status = "PUBLIC" if self.switches[0] == "public" else "PRIVATE"
        else:
            # Handle the traditional status=value format
            note_spec, status = self.args.split("=", 1)
            if "/" in note_spec:
                target_name, note_id = note_spec.split("/", 1)
                target = self.search_for_character(target_name)
                if not target:
                    return
            else:
                target = self.caller
                note_id = note_spec.strip()
            status = status.strip().upper()

        if status not in ["PRIVATE", "PUBLIC"]:
            self.caller.msg("Status must be either PRIVATE or PUBLIC.")
            return

        # Check permissions if trying to modify another character's notes
        if target != self.caller and not self.caller.check_permstring("Builders"):
            self.caller.msg("You don't have permission to modify notes on other characters.")
            return

        if target.update_note(note_id, is_public=(status == "PUBLIC")):
            self.caller.msg(f"Note #{note_id} on {target.name} is now {status}.")
            if target != self.caller:
                target.msg(f"Your note #{note_id} has been made {status} by {self.caller.name}.")
        else:
            self.caller.msg(f"Note #{note_id} not found on {target.name}.")

    def prove_note(self):
        if not self.args or "=" not in self.args:
            self.caller.msg("Usage: +note/prove <note name>=<target1>,<target2>,...")
            return

        note_name, targets = self.args.split("=", 1)
        note_name = note_name.strip()
        targets = [target.strip() for target in targets.split(",")]

        note = self.caller.get_note(note_name)
        if not note:
            self.caller.msg(f"Note not found: {note_name}")
            return

        for target_name in targets:
            target = self.search_for_character(target_name)
            if target:
                self.display_note(note, target)
                self.caller.msg(f"Note '{note_name}' shown to {target.name}.")
            else:
                self.caller.msg(f"Could not find character '{target_name}'.")

    def approve_note(self):
        """Approve a note (staff only)."""
        if not self.caller.check_permstring("Builders"):
            self.caller.msg("You don't have permission to approve notes.")
            return

        if not self.args:
            self.caller.msg("Usage: +note/approve <target>/<note>")
            return

        if "/" not in self.args:
            self.caller.msg("You must specify both target and note ID.")
            return

        target_name, note_id = self.args.split("/", 1)
        target = self.search_for_character(target_name)
        if not target:
            return

        note = target.get_note(note_id)
        if not note:
            self.caller.msg("No note with that ID exists.")
            return

        # Update note approval status
        target.update_note(note_id, 
            is_approved=True, 
            approved_by=self.caller.name,
            approved_at=datetime.now()
        )
        self.caller.msg(f"Note #{note_id} has been approved.")
        target.msg(f"Your note #{note_id} has been approved by {self.caller.name}.")

    def unapprove_note(self):
        """Unapprove a note (staff only)."""
        if not self.caller.check_permstring("Builders"):
            self.caller.msg("You don't have permission to unapprove notes.")
            return

        if not self.args:
            self.caller.msg("Usage: +note/unapprove <target>/<note>")
            return

        if "/" not in self.args:
            self.caller.msg("You must specify both target and note ID.")
            return

        target_name, note_id = self.args.split("/", 1)
        target = self.search_for_character(target_name)
        if not target:
            return

        note = target.get_note(note_id)
        if not note:
            self.caller.msg("No note with that ID exists.")
            return

        # Update note approval status
        target.update_note(note_id, 
            is_approved=False, 
            approved_by=None,
            approved_at=None
        )
        self.caller.msg(f"Note #{note_id} has been unapproved.")
        target.msg(f"Your note #{note_id} has been unapproved by {self.caller.name}.")

    def display_note(self, note):
        """Display a note with formatting."""
        width = 78
        output = header(f"Note #{note.note_id}", width=width, color="|y", fillchar="|r=|n", bcolor="|b")

        if note.category:
            output += f"|c{note.category}|n"
            output += f" |w#{note.note_id}|n\n"

        output += format_stat("Note Title:", note.name, width=width) + "\n"
        output += format_stat("Visibility:", "Public" if note.is_public else "Private", width=width) + "\n"
        
        # Show approval status and details
        if note.is_approved:
            output += format_stat("Approved:", "Yes", width=width) + "\n"
            if note.approved_by:
                output += format_stat("Approved By:", note.approved_by, width=width) + "\n"
            if note.approved_at:
                output += format_stat("Approved At:", note.approved_at.strftime("%Y-%m-%d %H:%M:%S"), width=width) + "\n"
        else:
            output += format_stat("Approved:", "No", width=width) + "\n"

        # Show creation and update times for staff
        if self.caller.check_permstring("Builders"):
            output += format_stat("Created:", note.created_at.strftime("%Y-%m-%d %H:%M:%S"), width=width) + "\n"
            output += format_stat("Updated:", note.updated_at.strftime("%Y-%m-%d %H:%M:%S"), width=width) + "\n"

        output += divider("", width=width, fillchar="-", color="|r") + "\n"
        
        # Note content
        content_lines = note.text.replace('|/', '\n').split('\n')
        wrapped_lines = []
        for line in content_lines:
            if line.strip():
                wrapped_lines.append(wrap_ansi(line.strip(), width=width-2))
        output += '\n'.join(wrapped_lines) + "\n"

        output += footer(width=width, fillchar="|r=|n")
        self.caller.msg(output)