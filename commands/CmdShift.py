from tempfile import TemporaryDirectory
from unicodedata import category
from evennia import default_cmds
from evennia.utils import evtable
from typeclasses.characters import Character
from world.wod20th.models import ShapeshifterForm, Stat
from world.wod20th.utils.formatting import format_stat

from random import randint
from typing import List, Tuple

def roll_dice(dice_pool: int, difficulty: int) -> Tuple[List[int], int, int]:
    rolls = [randint(1, 10) for _ in range(max(0, dice_pool))]
    successes = sum(1 for roll in rolls if roll >= difficulty)
    ones = sum(1 for roll in rolls if roll == 1)
    
    # If there are any successes, subtract ones from them
    if successes > 0:
        successes = max(0, successes - ones)
        return rolls, successes, ones
    
    # If there are no successes AND there are ones, it's a botch
    if successes == 0 and ones > 0:
        return rolls, -1, ones  # Indicate botch with -1
    
    # No successes but also no ones - just a failure
    return rolls, 0, ones

def interpret_roll_results(successes, ones, diff=6, rolls=None):
    # A botch only occurs if there are no successes AND there are ones
    is_botch = successes < 0
    
    success_string = f"|g{successes}|n" if successes > 0 else f"|y{successes}|n" if successes == 0 else f"|r{successes}|n"
    
    msg = f"|w(|n{success_string}|w)|n"
    if is_botch:
        msg += f"|r Botch!|n"
    else:
        msg += "|y Successes|n" if successes != 1 else "|y Success|n"
    
    if rolls:
        msg += " |w(|n"
        rolls.sort(reverse=True)
        msg += " ".join(f"|r{roll}|n" if roll == 1 else f"|g{roll}|n" if roll >= diff else f"|y{roll}|n" for roll in rolls)
        msg += "|w)|n"
    
    return msg

class CmdShift(default_cmds.MuxCommand):
    """
    Change your character's shapeshifter form.

    Usage:
      +shift <form name>
      +shift/roll <form name>
      +shift/rage <form name>
      +shift/message <form name> = <your custom message>
      +shift/setdeedname <deed name>
      +shift/setformname <form name> = <form-specific name>
      +shift/name <form name> = <new name>
      +shift/list

    Switches:
      /roll - Roll to determine if the shift is successful
      /rage - Spend Rage points to guarantee a successful shift
      /message - Set your personal custom shift message for the specified form
      /setdeedname - Set your character's deed name for use in most shifted forms
      /setformname - Set a specific name for the character when in a particular form
      /name - Set a new name for the form you're shifting into
      /list - Display all available forms for your character

    This command allows you to change your character's shapeshifter form.
    Without switches, it will attempt to shift using the default method.
    The /roll switch will make a roll to determine success.
    The /rage switch will spend Rage points to guarantee success.
    The /message switch allows you to set your personal custom shift message for a form.
    The /setdeedname switch sets your character's deed name for use in most shifted forms.
    The /setformname switch lets you set a specific name for your character when in a particular form.
    The /name switch allows you to set a new name for the form you're shifting into.
    The /list switch displays all available forms for your character.

    In shift messages, use {truename} for the character's true name, {deedname} for the deed name,
    and {formname} for the form-specific name (if set).
    """

    key = "+shift"
    aliases = ["shift"]
    locks = "cmd:all()"
    help_category = "Shapeshifting"

    def func(self):
        if "debug" in self.switches:
            # No need to re-import ShapeshifterForm here since it's imported at the top
            all_forms = ShapeshifterForm.objects.all()
            
            if not all_forms:
                self.caller.msg("No forms found in database.")
                return
                
            table = evtable.EvTable(
                "|wForm Name|n",
                "|wShifter Type|n",
                "|wStat Modifiers|n",
                "|wDifficulty|n",
                border="header"
            )
            
            for form in all_forms:
                mods = ", ".join([f"{stat} {mod:+d}" for stat, mod in form.stat_modifiers.items()])
                table.add_row(
                    form.name,
                    form.shifter_type,
                    mods,
                    str(form.difficulty)
                )
            
            self.caller.msg(table)
            return
            
        character = self.caller

        # Check if the character is a Shifter
        splat = character.get_stat('other', 'splat', 'Splat', temp=False)
        if splat.lower() != 'shifter':
            self.caller.msg("Only Shifters can use the +shift command.")
            return

        if not self.args and not self.switches:
            self.caller.msg("Usage: +shift <form name>")
            return

        if not self.is_valid_character(character):
            self.caller.msg("You need to have a valid character to use this command.")
            return
        
        if "list" in self.switches:
            self._list_available_forms()
            return
        elif "message" in self.switches:
            self._set_custom_message(character)
            return
        elif "setdeedname" in self.switches:
            self._set_deed_name(character)
            return
        elif "setformname" in self.switches:
            self._set_form_name(character)
            return
        elif "name" in self.switches:
            self._set_form_name_with_shift(character)
            return

        form_name = self.args.strip()
        try:
            # Get the character's shifter type
            shifter_type = self.caller.db.stats.get('identity', {}).get('lineage', {}).get('Type', {}).get('perm', '').lower()
            
            # Look up form by both name and shifter type
            form = ShapeshifterForm.objects.get(
                name__iexact=form_name,
                shifter_type=shifter_type
            )
        except ShapeshifterForm.DoesNotExist:
            self.caller.msg(f"The form '{form_name}' is not available to your shifter type.")
            return
        except ShapeshifterForm.MultipleObjectsReturned:
            self.caller.msg(f"Error: Multiple forms found with name '{form_name}'. Please contact an admin.")
            return

        if "roll" in self.switches:
            success = self._shift_with_roll(character, form)
        elif "rage" in self.switches:
            success = self._shift_with_rage(character, form)
        else:
            success = self._shift_default(character, form)

        if success:
            self._apply_form_changes(character, form)
            self._display_shift_message(character, form)

    def is_valid_character(self, obj):
        """
        Check if the given object is a valid character based on its 'stats' attribute structure.
        """
        return True

    def _list_available_forms(self):
        character = self.caller
        shifter_type = character.db.stats.get('identity', {}).get('lineage', {}).get('Type', {}).get('perm', '').lower()
        
        # Get all available forms for the character's shifter type
        if shifter_type == 'ananasi':
            available_forms = ShapeshifterForm.objects.filter(shifter_type='ananasi').order_by('name')
        elif shifter_type == 'ajaba':
            available_forms = ShapeshifterForm.objects.filter(shifter_type='ajaba').order_by('name')
        elif shifter_type == 'bastet':
            available_forms = ShapeshifterForm.objects.filter(shifter_type='bastet').order_by('name')
        elif shifter_type == 'corax':
            available_forms = ShapeshifterForm.objects.filter(shifter_type='corax').order_by('name')
        elif shifter_type == 'garou':
            available_forms = ShapeshifterForm.objects.filter(shifter_type='garou').order_by('name')
        elif shifter_type == 'gurahl':
            available_forms = ShapeshifterForm.objects.filter(shifter_type='gurahl').order_by('name')
        elif shifter_type == 'ratkin':
            available_forms = ShapeshifterForm.objects.filter(shifter_type='ratkin').order_by('name')
        elif shifter_type == 'rokea':
            available_forms = ShapeshifterForm.objects.filter(shifter_type='rokea').order_by('name')
        else:
            self.caller.msg(f"Unknown shifter type: {shifter_type}")
            return

        # Always include Homid form for shapeshifters that can use it
        homid_capable = ['garou', 'ananasi', 'ajaba', 'bastet', 'corax', 'gurahl', 'ratkin']
        if shifter_type.lower() in homid_capable:
            homid_form = ShapeshifterForm.objects.filter(name__iexact='homid').first()
        else:
            homid_form = None
        
        table = evtable.EvTable(
            "|wForm|n",
            "|wStat Modifiers|n",
            "|wDifficulty|n",
            border="header"
        )
        
        if homid_form:
            table.add_row("Homid", "Base Stats", "6")
        
        for form in available_forms:
            if form.name.lower() != 'homid':
                mods = ", ".join([f"{stat} {mod:+d}" for stat, mod in form.stat_modifiers.items()])
                table.add_row(form.name, mods, str(form.difficulty))
        
        if not available_forms and not homid_form:
            self.caller.msg(f"No forms found for shifter type: {shifter_type}")
            return
            
        self.caller.msg(table)

    def _reset_stats(self, character):
        # Reset all stats that can be modified by shapeshifting
        stats_to_reset = ['strength', 'dexterity', 'stamina', 'charisma', 'manipulation', 'appearance', 'perception', 'intelligence', 'wits']
        for stat in stats_to_reset:
           stat_obj = Stat.objects.get(name__iexact=stat, category='attributes')
           if stat_obj.category and stat_obj.stat_type:
               curr_stat = character.get_stat(stat_obj.category, stat_obj.stat_type, stat_obj.name)
               character.set_stat(stat_obj.category, stat_obj.stat_type, stat_obj.name, curr_stat, temp=True)

    def _shift_with_roll(self, character, form):
        """Attempt to shift using a dice roll."""
        primal_urge = character.get_stat('abilities', 'talent', 'Primal-Urge', temp=False) or 0
        stamina = character.get_stat('attributes', 'physical', 'Stamina', temp=False) or 0
        
        dice_pool = primal_urge + stamina
        difficulty = form.difficulty
        
        rolls, successes, ones = roll_dice(dice_pool, difficulty)
        
        self.caller.msg(f"Rolling {dice_pool} dice (Primal-Urge {primal_urge} + Stamina {stamina}) against difficulty {difficulty}.")
        self.caller.msg(f"Roll result: {interpret_roll_results(successes, ones, difficulty, rolls)}")
        
        # A botch is indicated by successes being -1
        if successes < 0:
            self.caller.msg(f"Failure. You are unable to shift into {form.name} form.")
            return False
        elif successes > 0:
            self.caller.msg(f"Success! You shift into {form.name} form.")
            self._reset_stats(character)  # Reset stats before applying new form
            return True
        else:
            self.caller.msg(f"Failure. You are unable to shift into {form.name} form.")
            return False

    def _shift_with_rage(self, character, form):
        current_rage = character.db.stats.get('pools', {}).get('dual', {}).get('Rage', {}).get('temp', 0)
        if current_rage >= 1:
            # Spend 1 Rage point for automatic shift
            character.db.stats['pools']['dual']['Rage']['temp'] = current_rage - 1
            self.caller.msg(f"You spend a point of Rage to force the change into {form.name} form. (Remaining Rage: {current_rage - 1})")
            return True
        else:
            self.caller.msg("You don't have any Rage points to spend for an automatic shift.")
            return False

    def _shift_default(self, character, form):
        # Get character's breed form
        breed = character.db.stats.get('other', {}).get('identity', {}).get('Breed', {}).get('perm', 'homid').lower()
        shifter_type = character.db.stats.get('other', {}).get('identity', {}).get('Shifter Type', {}).get('perm', '').lower()
        
        # Check if they're shifting to their breed form
        if shifter_type == 'garou':
            if (breed == 'homid' and form.name.lower() == 'homid' or
                breed == 'metis' and form.name.lower() == 'crinos' or
                breed == 'lupus' and form.name.lower() == 'lupus'):
                self.caller.msg(f"You easily shift back to your natural {form.name} form.")
                return True
        
        # If not shifting to breed form, use the roll method
        return self._shift_with_roll(character, form)

    def _apply_form_changes(self, character, form):
        # Reset stats to base values first
        self._reset_stats(character)
        
        # If it's Homid form, we're done (using base stats)
        if form.name.lower() == 'homid':
            character.db.current_form = 'Homid'
            return
        
        # Apply stat modifiers for non-Homid forms
        for stat, modifier in form.stat_modifiers.items():
            stat_obj = Stat.objects.get(name__iexact=stat)
            
            if stat_obj.category and stat_obj.stat_type:
                current_value = character.get_stat(stat_obj.category, stat_obj.stat_type, stat_obj.name, temp=False)
                
                # Handle special case where Appearance is set to 0
                if stat.lower() == 'appearance' and modifier == 0:
                    new_value = 0
                else:
                    new_value = current_value + modifier
                
                # Ensure stats don't go below 0 or above 10
                new_value = max(0, min(10, new_value))
                
                character.set_stat(stat_obj.category, stat_obj.stat_type, stat_obj.name, new_value, temp=True)
                self.caller.msg("|YSHIFT>|n" + format_stat(stat_obj.name, current_value) + f" -> |g{new_value}|n")

    def _display_shift_message(self, character, form):
        """Display the appropriate shift message."""
        # Get the custom message for this form if it exists
        custom_message = character.attributes.get(f"shift_message_{form.name.lower()}")
        
        if custom_message:
            # Replace placeholders in custom message
            message = custom_message.format(
                truename=character.key,
                deedname=character.db.deed_name or character.key,
                formname=self._get_form_name(character, form)
            )
            self.caller.location.msg_contents(message)
        else:
            # Default message if no custom message exists
            self.caller.location.msg_contents(
                f"{character.key} shifts into {form.name} form."
            )

        # Change the character's visible name
        character.db.current_form = form.name
        if form.name.lower() == 'homid':
            character.db.display_name = character.db.original_name
        else:
            character.db.display_name = form.name

        # Add the original name as an alias if it's not already there
        if character.db.original_name not in character.aliases.all():
            character.aliases.add(character.db.original_name)

    def _get_player_custom_message(self, character, form):
        return character.attributes.get(f"shift_message_{form.name.lower()}", None)

    def _set_custom_message(self, character):
        if "=" not in self.args:
            self.caller.msg("Usage: +shift/message <form name> = <your custom message>")
            return

        form_name, message = self.args.split("=", 1)
        form_name = form_name.strip()
        message = message.strip()

        try:
            form = ShapeshifterForm.objects.get(name__iexact=form_name)
        except ShapeshifterForm.DoesNotExist:
            self.caller.msg(f"The form '{form_name}' does not exist.")
            return

        character.attributes.add(f"shift_message_{form_name.lower()}", message)
        self.caller.msg(f"Your personal shift message set for {form_name} form.")

    def _set_deed_name(self, character):
        deed_name = self.args.strip()
        if not deed_name:
            self.caller.msg("Usage: +shift/setdeedname <deed name>")
            return

        character.db.deed_name = deed_name
        self.caller.msg(f"Your deed name has been set to: {deed_name}")

    def _set_form_name(self, character):
        if "=" not in self.args:
            self.caller.msg("Usage: +shift/setformname <form name> = <form-specific name>")
            return

        form_name, form_specific_name = self.args.split("=", 1)
        form_name = form_name.strip()
        form_specific_name = form_specific_name.strip()

        try:
            form = ShapeshifterForm.objects.get(name__iexact=form_name)
        except ShapeshifterForm.DoesNotExist:
            self.caller.msg(f"The form '{form_name}' does not exist.")
            return

        character.attributes.add(f"form_name_{form_name.lower()}", form_specific_name)
        self.caller.msg(f"Your name for {form_name} form set to: {form_specific_name}")

        # Update display_name if the character is currently in this form
        if character.db.current_form and character.db.current_form.lower() == form_name.lower():
            character.db.display_name = form_specific_name

    def _set_form_name_with_shift(self, character):
        if "=" not in self.args:
            self.caller.msg("Usage: +shift/name <form name> = <new name>")
            return

        form_name, new_name = self.args.split("=", 1)
        form_name = form_name.strip()
        new_name = new_name.strip()

        try:
            form = ShapeshifterForm.objects.get(name__iexact=form_name)
        except ShapeshifterForm.DoesNotExist:
            self.caller.msg(f"The form '{form_name}' does not exist.")
            return

        character.attributes.add(f"form_name_{form_name.lower()}", new_name)
        self.caller.msg(f"Your name for {form_name} form set to: {new_name}")

        # Perform the shift
        success = self._shift_default(character, form)
        if success:
            self._apply_form_changes(character, form)
            self._display_shift_message(character, form)

    def _get_form_name(self, character, form):
        if form.name.lower() == 'homid':
            return character.db.original_name or character.db.gradient_name or character.key
        return character.attributes.get(f"form_name_{form.name.lower()}", character.db.deed_name or character.db.gradient_name or character.key)

    def _apply_form_modifiers(self, character, form):
        """Apply stat modifiers from the form."""
        # First reset all stats
        self._reset_stats(character)
        
        # List of forms that set Appearance to 0
        zero_appearance_forms = [
            'crinos',      # All shapeshifters
            'anthros',     # Ajaba war form
            'arthren',     # Gurahl war form
            'sokto',       # Bastet war form
            'chatro'       # Bastet battle form
        ]

        # Debug output
        print(f"Form name: {form.name.lower()}")
        print(f"Is zero appearance form? {form.name.lower() in zero_appearance_forms}")
        print(f"Current Appearance: {character.get_stat('attributes', 'social', 'Appearance', temp=True)}")

        # Handle Appearance first to ensure it takes precedence
        if form.name.lower() in zero_appearance_forms:
            stat_obj = Stat.objects.get(name__iexact='appearance', category='attributes')
            # Force temp value to 0 and add a flag to indicate it should stay 0
            character.set_stat(stat_obj.category, stat_obj.stat_type, stat_obj.name, 0, temp=True)
            character.attributes.add('appearance_override', True)
            print(f"Set appearance to 0 and added override flag")
            print(f"New Appearance value: {character.get_stat('attributes', 'social', 'Appearance', temp=True)}")
        else:
            # Clear the override flag if it exists
            character.attributes.remove('appearance_override')
            print(f"Removed override flag")

        # Then apply all other modifiers
        for stat, mod in form.stat_modifiers.items():
            if stat.lower() != 'appearance':  # Skip Appearance since we handled it above
                stat_obj = Stat.objects.get(name__iexact=stat, category='attributes')
                if stat_obj.category and stat_obj.stat_type:
                    current_stat = character.get_stat(stat_obj.category, stat_obj.stat_type, stat_obj.name)
                    new_value = current_stat + mod
                    character.set_stat(stat_obj.category, stat_obj.stat_type, stat_obj.name, new_value, temp=True)
