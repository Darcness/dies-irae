from evennia import DefaultRoom
from evennia.utils.utils import make_iter, justify
from evennia.utils.ansi import ANSIString
from evennia.utils import ansi
from world.wod20th.utils.ansi_utils import wrap_ansi
from world.wod20th.utils.formatting import header, footer, divider
from datetime import datetime
import random
from evennia.utils.search import search_channel

class RoomParent(DefaultRoom):

    def get_display_name(self, looker, **kwargs):
        """
        Get the name to display for the character.
        """
        
        name = self.key
        
        if self.db.gradient_name:
            name = ANSIString(self.db.gradient_name)
            if looker.check_permstring("builders"):
                name += f"({self.dbref})"
            return name
        
        # If the looker is builder+ show the dbref
        if looker.check_permstring("builders"):
            name += f"({self.dbref})"

        return name

    def return_appearance(self, looker, **kwargs):
        if not looker:
            return ""

        name = self.get_display_name(looker, **kwargs)
        
        # Check if the looker is in the Umbra or peeking into it
        in_umbra = looker.tags.get("in_umbra", category="state")
        peeking_umbra = kwargs.get("peek_umbra", False)
        
        # Set color scheme based on umbra state
        border_color = "|B" if (in_umbra or peeking_umbra) else "|r"
        
        # Choose the appropriate description
        if (in_umbra or peeking_umbra) and self.db.umbra_desc:
            desc = self.db.umbra_desc
        else:
            desc = self.db.desc

        # Update all dividers to use the new color scheme
        string = header(name, width=78, bcolor=border_color, fillchar=ANSIString(f"{border_color}-|n")) + "\n"
        
        # Process room description
        if desc:
            # Process description while preserving ANSI codes
            desc = str(desc)  # Start with raw string to preserve all codes
            
            # Split description into paragraphs using %R or %r while preserving ANSI
            paragraphs = []
            for p in desc.split('%R'):
                paragraphs.extend(p.split('%r'))
            
            formatted_paragraphs = []
            for paragraph in paragraphs:
                if not paragraph.strip():
                    continue
                
                # Split paragraph into lines by tabs
                tab_lines = []
                for line in paragraph.split('%t'):
                    tab_lines.extend(line.split('%T'))
                
                formatted_lines = []
                for i, line in enumerate(tab_lines):
                    line = line.strip()
                    if i > 0:  # Add indentation for tabbed lines
                        # Check if line starts with a color code
                        if line.startswith('|'):
                            color_end = line.find(' ')
                            if color_end > 0:
                                # Preserve color code and add indentation after it
                                color_code = line[:color_end]
                                rest_of_line = line[color_end:].strip()
                                line = f"{color_code}    {rest_of_line}"
                            else:
                                line = "    " + line
                        else:
                            line = "    " + line
                    
                    # Process line for word wrapping while preserving ANSI
                    wrapped = wrap_ansi(line, width=78)
                    if wrapped:
                        formatted_lines.append(wrapped)
                
                if formatted_lines:
                    formatted_paragraphs.append("\n".join(formatted_lines))
            
            # Join all paragraphs with single newlines
            string += "\n".join(formatted_paragraphs) + "\n"

        # List all characters in the room
        characters = []
        for obj in self.contents:
            if obj.has_account:
                # Use tag state for comparison
                obj_umbra_tag = obj.tags.get("in_umbra", category="state")
                looker_umbra_tag = looker.tags.get("in_umbra", category="state")
                
                if obj_umbra_tag == looker_umbra_tag:
                    characters.append(obj)

        if characters:
            string += divider("Characters", width=78, fillchar=ANSIString(f"{border_color}-|n")) + "\n"
            for character in characters:
                idle_time = self.idle_time_display(character.idle_time)

                shortdesc = character.db.shortdesc
                if shortdesc:
                    shortdesc_str = f"{shortdesc}"
                else:
                    shortdesc_str ="|h|xType '|n+shortdesc <desc>|h|x' to set a short description.|n"

                if len(ANSIString(shortdesc_str).strip()) > 60:
                    shortdesc_str = ANSIString(shortdesc_str)[:60]
                    shortdesc_str = ANSIString(shortdesc_str[:-3] + "...|n")
                else:
                    shortdesc_str = ANSIString(shortdesc_str).ljust(60, ' ')
                
                string += ANSIString(f" {character.get_display_name(looker).ljust(12)} {ANSIString(idle_time).rjust(7)}|n {shortdesc_str}\n")

        # List all objects in the room
        objects = [obj for obj in self.contents if not obj.has_account and not obj.destination]
        if objects:
            string += divider("Objects", width=78, fillchar=ANSIString(f"{border_color}-|n")) + "\n"
            
            # get shordesc or dhoe s blsnk string
            for obj in objects:
                if obj.db.shortdesc:
                    shortdesc = obj.db.shortdesc
                else:
                    shortdesc = ""


            # if looker builder+ show dbref.

                string +=" "+  ANSIString(f"{obj.get_display_name(looker)}").ljust(25) + ANSIString(f"{shortdesc}") .ljust(53, ' ') + "\n"

        # List all exits
        exits = [ex for ex in self.contents if ex.destination]
        if exits:
            direction_strings = []
            exit_strings = []
            for exit in exits:
                aliases = exit.aliases.all() or []
                exit_name = exit.get_display_name(looker)
                short = min(aliases, key=len) if aliases else ""
                
                exit_string = ANSIString(f" <|y{short.upper()}|n> {exit_name}")
                
                if any(word in exit_name for word in ['Sector', 'District', 'Neighborhood']):
                    direction_strings.append(exit_string)
                else:
                    exit_strings.append(exit_string)

            # Display Directions
            if direction_strings:
                string += divider("Directions", width=78, fillchar=ANSIString(f"{border_color}-|n")) + "\n"
                string += self.format_exit_columns(direction_strings)

            # Display Exits
            if exit_strings:
                string += divider("Exits", width=78, fillchar=ANSIString(f"{border_color}-|n")) + "\n"
                string += self.format_exit_columns(exit_strings) + "\n"

        # Get room type and resources
        room_type = self.db.roomtype or "Unknown"
        resources = self.db.resources
        resources_str = f"Res:{resources}" if resources is not None else ""

        # Create the footer with room type and resources
        footer_text = f"{resources_str}, {room_type}".strip(", ")
        footer_length = len(ANSIString(footer_text))
        padding = 78 - footer_length - 2  # -2 for the brackets

        string += ANSIString(f"{border_color}{'-' * padding}[|c{footer_text}{border_color}]|n")

        return string

    def format_exit_columns(self, exit_strings):
        # Split into two columns
        half = (len(exit_strings) + 1) // 2
        col1 = exit_strings[:half]
        col2 = exit_strings[half:]

        # Create two-column format
        formatted_string = ""
        for i in range(max(len(col1), len(col2))):
            col1_str = col1[i] if i < len(col1) else ANSIString("")
            col2_str = col2[i] if i < len(col2) else ANSIString("")
            formatted_string += f"{col1_str.ljust(38)} {col2_str}\n"
        
        return formatted_string

    def idle_time_display(self, idle_time):
        """
        Formats the idle time display.
        """
        idle_time = int(idle_time)  # Convert to int
        if idle_time < 60:
            time_str = f"{idle_time}s"
        elif idle_time < 3600:
            time_str = f"{idle_time // 60}m"
        else:
            time_str = f"{idle_time // 3600}h"

        # Color code based on idle time intervals
        if idle_time < 900:  # less than 15 minutes
            return ANSIString(f"|g{time_str}|n")  # green
        elif idle_time < 1800:  # 15-30 minutes
            return ANSIString(f"|y{time_str}|n")  # yellow
        elif idle_time < 2700:  # 30-45 minutes
            return ANSIString(f"|r{time_str}|n")  # orange (using red instead)
        elif idle_time < 3600:
            return ANSIString(f"|R{time_str}|n")  # bright red
        else:
            return ANSIString(f"|x{time_str}|n")  # grey

    def get_gauntlet_difficulty(self):
        """
        Returns the Gauntlet difficulty for this room, including any temporary modifiers.
        """
        base_difficulty = self.db.gauntlet_difficulty or 6  # Default difficulty
        temp_modifier = self.db.temp_gauntlet_modifier or 0
        
        # Get the expiry time for the modifier
        modifier_expiry = self.db.temp_gauntlet_expiry or 0
        
        # Check if the modifier has expired
        if modifier_expiry and datetime.now().timestamp() > modifier_expiry:
            # Clear expired modifier
            self.db.temp_gauntlet_modifier = 0
            self.db.temp_gauntlet_expiry = None
            return base_difficulty
        
        return max(1, base_difficulty + temp_modifier)  # Ensure difficulty never goes below 1

    def modify_gauntlet(self, modifier, duration=0):
        """
        Temporarily modifies the Gauntlet difficulty of the room.
        
        Args:
            modifier (int): The amount to modify the Gauntlet by (negative numbers lower it)
            duration (int): How long in seconds the modification should last (0 for permanent)
        """
        self.db.temp_gauntlet_modifier = modifier
        
        if duration > 0:
            self.db.temp_gauntlet_expiry = datetime.now().timestamp() + duration
        else:
            self.db.temp_gauntlet_expiry = None
        
        # Announce the change if it's significant
        if modifier < 0:
            self.msg_contents("The Gauntlet seems to thin in this area...")
        elif modifier > 0:
            self.msg_contents("The Gauntlet seems to thicken in this area...")

    def modify_gauntlet(self, modifier, duration=0):
        """
        Temporarily modifies the Gauntlet difficulty of the room.
        
        Args:
            modifier (int): The amount to modify the Gauntlet by (negative numbers lower it)
            duration (int): How long in seconds the modification should last (0 for permanent)
        """
        self.db.temp_gauntlet_modifier = modifier
        
        if duration > 0:
            self.db.temp_gauntlet_expiry = datetime.now().timestamp() + duration
        else:
            self.db.temp_gauntlet_expiry = None
        
        # Announce the change if it's significant
        if modifier < 0:
            self.msg_contents("The Gauntlet seems to thin in this area...")
        elif modifier > 0:
            self.msg_contents("The Gauntlet seems to thicken in this area...")

    def peek_umbra(self, looker):
        """Allow a character to peek into the Umbra version of the room."""
        # Use the same return_appearance method but with peek_umbra flag
        appearance = self.return_appearance(looker, peek_umbra=True)
        
        # Extract just the description part (between header and first divider)
        lines = appearance.split('\n')
        desc_lines = []
        for line in lines[2:]:  # Skip header lines
            if line.startswith('---'):  # Stop at first divider
                break
            desc_lines.append(line)
        
        header = "-" * 30 + "<  Umbra Vision >" + "-" * 31
        footer = "-" * 78
        
        return f"\n{header}\n\n{''.join(desc_lines)}\n{footer}"

    def format_description(self, desc):
        """
        Format the description with proper paragraph handling and indentation.
        """
        paragraphs = desc.split('%r', '%R')
        formatted_paragraphs = []
        for i, p in enumerate(paragraphs):
            if not p.strip():
                if i > 0 and not paragraphs[i-1].strip():
                    formatted_paragraphs.append('')  # Add blank line for double %r
                continue
            
            lines = p.split('%t')
            formatted_lines = []
            for j, line in enumerate(lines):
                if j == 0 and line.strip():
                    formatted_lines.append(wrap_ansi(line.strip(), width=76))
                elif line.strip():
                    formatted_lines.append(wrap_ansi('    ' + line.strip(), width=76))
            
            formatted_paragraphs.append('\n'.join(formatted_lines))

        
        # Rejoin lines and handle other formatting
        desc = '\n'.join(lines)
        desc = desc.replace('%R', '\n')
        desc = desc.replace('%r', '\n')
        
        # Split into paragraphs and rejoin with proper spacing
        paragraphs = [p.strip() for p in desc.split('\n') if p.strip()]
        return '\n\n'.join(paragraphs)

    def msg_contents(self, text=None, exclude=None, from_obj=None, mapping=None, **kwargs):
        """
        Send a message to all objects inside the room, excluding the sender and those in a different plane.
        """
        contents = self.contents
        if exclude:
            exclude = make_iter(exclude)
            contents = [obj for obj in contents if obj not in exclude]

        for obj in contents:
            if hasattr(obj, 'is_character') and obj.is_character:
                # Check if the character is in the same plane (Umbra or material)
                if from_obj and hasattr(from_obj, 'tags'):
                    sender_in_umbra = from_obj.tags.get("in_umbra", category="state")
                    receiver_in_umbra = obj.tags.get("in_umbra", category="state")
                    
                    if sender_in_umbra != receiver_in_umbra:
                        continue  # Skip this character if they're in a different plane

            obj.msg(text=text, from_obj=from_obj, mapping=mapping, **kwargs)

    def step_sideways(self, character):
        """
        Allows a character to step sideways into the Umbra.
        """
        difficulty = self.get_gauntlet_difficulty()
        successes, ones = self.roll_gnosis(character, difficulty)
        
        if successes > 0:
            character.tags.remove("in_material", category="state")
            character.tags.add("in_umbra", category="state")
            character.msg("You successfully step sideways into the Umbra.")
            self.msg_contents(f"{character.name} shimmers and fades from view as they step into the Umbra.", exclude=character, from_obj=character)
            return True
        elif successes == 0 and ones > 0:
            # Botch
            character.msg("You catastrophically fail to step sideways into the Umbra.")
            self.msg_contents(f"{character.name} seems to flicker for a moment, but remains in place.", exclude=character, from_obj=character)
            
            # Announce the botch on the mudinfo channel
            mudinfo = search_channel("mudinfo")
            if mudinfo:
                mudinfo[0].msg(f"|rBOTCH!!!|n {character.name} botched their attempt to step sideways in {self.name}.")
            
            return False
        else:
            character.msg("You fail to step sideways into the Umbra.")
            return False

    def return_from_umbra(self, character):
        """
        Allows a character to return from the Umbra to the material world.
        """
        difficulty = self.get_gauntlet_difficulty()
        successes, ones = self.roll_gnosis(character, difficulty)
        
        if successes > 0:
            character.tags.remove("in_umbra", category="state")
            character.tags.add("in_material", category="state")
            character.msg("You step back into the material world.")
            self.msg_contents(f"{character.name} shimmers into view as they return from the Umbra.", exclude=character, from_obj=character)
            return True
        elif successes == 0 and ones > 0:
            # Botch
            character.msg("You catastrophically fail to return from the Umbra.")
            
            # Announce the botch on the mudinfo channel
            mudinfo = search_channel("mudinfo")
            if mudinfo:
                mudinfo[0].msg(f"|rBOTCH!!!|n {character.name} botched their attempt to return from the Umbra in {self.name}.")
            
            return False
        else:
            character.msg("You fail to return from the Umbra.")
            return False

    def roll_gnosis(self, character, difficulty):
        """
        Simulates a Gnosis roll for the character.
        Returns a tuple of (successes, ones).
        """
        stats = character.db.stats
        if not stats or 'pools' not in stats or 'dual' not in stats['pools'] or 'Gnosis' not in stats['pools']['dual']:
            character.msg("Error: Gnosis attribute not found. Please contact an admin.")
            return 0, 0
        
        gnosis = stats['pools']['dual']['Gnosis']['perm']
        if gnosis is None:
            character.msg("Error: Permanent Gnosis value is None. Please contact an admin.")
            return 0, 0
        
        # Convert gnosis to an integer if it's stored as a string
        if isinstance(gnosis, str):
            try:
                gnosis = int(gnosis)
            except ValueError:
                character.msg("Error: Invalid Gnosis value. Please contact an admin.")
                return 0, 0
        
        successes = 0
        ones = 0
        for _ in range(gnosis):
            roll = random.randint(1, 10)
            if roll >= difficulty:
                successes += 1
            elif roll == 1:
                ones += 1
        
        character.msg(f"Gnosis Roll: {successes} successes against difficulty {difficulty}")
        return successes, ones
    
    def initialize(self):
        """
        Initialize default attributes if they haven't been set yet.
        This method can be called on already created objects.
        """
        if not self.attributes.has("initialized"):
            # Initialize attributes
            self.db.location_type = None  # "District", "Sector", "Neighborhood", or "Site"
            self.db.order = 0
            self.db.infrastructure = 0
            self.db.resolve = 0
            self.db.resources = {}  # Empty dict for resources
            self.db.owners = []
            self.db.sub_locations = []
            self.db.roll_log = []  # Initialize an empty list for roll logs
            self.db.initialized = True  # Mark this room as initialized
            self.save()  # Save immediately to avoid ID-related issues
        else:
            # Ensure roll_log exists even for previously initialized rooms
            if not hasattr(self.db, 'roll_log'):
                self.db.roll_log = []

    def at_object_creation(self):
        """
        Called when the room is first created.
        """
        super().at_object_creation()
        self.db.unfindable = False  # Add this line
        self.db.fae_desc = ""
        self.db.roll_log = []  # Initialize empty roll log

    def set_as_district(self):
        self.initialize()
        self.db.location_type = "District"

    def set_as_sector(self):
        self.initialize()
        self.db.location_type = "Sector"

    def set_as_neighborhood(self):
        self.initialize()
        self.db.location_type = "Neighborhood"
        self.db.order = 5
        self.db.infrastructure = 5
        self.db.resolve = 5

    def set_as_site(self):
        self.initialize()
        self.db.location_type = "Site"

    def add_sub_location(self, sub_location):
        """
        Add a sub-location to this room. Automatically sets the type of the sub-location.
        """
        self.initialize()
        sub_location.initialize()

        if self.db.location_type == "District":
            sub_location.set_as_sector()
        elif self.db.location_type == "Sector":
            sub_location.set_as_neighborhood()
        elif self.db.location_type == "Neighborhood":
            sub_location.set_as_site()

        self.db.sub_locations.append(sub_location)
        sub_location.db.parent_location = self
        self.save()  # Ensure changes are saved

    def remove_sub_location(self, sub_location):
        """
        Remove a sub-location from this room.
        """
        self.initialize()
        sub_location.initialize()
        if sub_location in self.db.sub_locations:
            self.db.sub_locations.remove(sub_location)
            sub_location.db.parent_location = None
            self.save()  # Ensure changes are saved

    def get_sub_locations(self):
        self.initialize()
        return self.db.sub_locations

    def update_values(self):
        """
        Update the Order, Infrastructure, and Resolve values based on the averages of sub-locations.
        Only applies if this room is a District or Sector.
        """
        self.initialize()
        if self.db.location_type in ["District", "Sector"]:
            sub_locations = self.get_sub_locations()
            if sub_locations:
                averages = {
                    "avg_order": sum(loc.db.order for loc in sub_locations) / len(sub_locations),
                    "avg_infrastructure": sum(loc.db.infrastructure for loc in sub_locations) / len(sub_locations),
                    "avg_resolve": sum(loc.db.resolve for loc in sub_locations) / len(sub_locations),
                }
                self.db.order = averages['avg_order']
                self.db.infrastructure = averages['avg_infrastructure']
                self.db.resolve = averages['avg_resolve']
            else:
                self.db.order = 0
                self.db.infrastructure = 0
                self.db.resolve = 0
            self.save()

    def save(self, *args, **kwargs):
        """
        Overriding save to ensure initialization happens after the object is fully created.
        """
        super().save(*args, **kwargs)
        self.initialize()
        if self.db.location_type in ["Sector", "Neighborhood"] and hasattr(self.db, "parent_location"):
            self.db.parent_location.update_values()

    def increase_order(self, amount=1):
        self.db.order += amount
        self.save()

    def decrease_order(self, amount=1):
        self.db.order = max(0, self.db.order - amount)
        self.save()

    def set_order(self, value):
        self.db.order = value
        self.save()

    def increase_infrastructure(self, amount=1):
        self.db.infrastructure += amount
        self.save()

    def decrease_infrastructure(self, amount=1):
        self.db.infrastructure = max(0, self.db.infrastructure - amount)
        self.save()

    def set_infrastructure(self, value):
        self.db.infrastructure = value
        self.save()

    def increase_resolve(self, amount=1):
        self.db.resolve += amount
        self.save()

    def decrease_resolve(self, amount=1):
        self.db.resolve = max(0, self.db.resolve - amount)
        self.save()

    def set_resolve(self, value):
        self.db.resolve = value
        self.save()

    def add_owner(self, owner):
        self.initialize()
        if owner not in self.db.owners:
            self.db.owners.append(owner)
            self.save()

    def remove_owner(self, owner):
        self.initialize()
        if owner in self.db.owners:
            self.db.owners.remove(owner)
            self.save()

    def display_hierarchy(self, depth=0):
        """
        Display the hierarchy of locations.
        """
        self.initialize()
        indent = "  " * depth
        self.msg(f"{indent}- {self.key} ({self.db.location_type})")
        for sub_loc in self.get_sub_locations():
            sub_loc.display_hierarchy(depth + 1)

    def log_roll(self, roller, description, result):
        """
        Log a dice roll in this room.
        
        Args:
            roller (str): Name of the character making the roll
            description (str): Description of the roll
            result (str): Result of the roll
        """
        if not hasattr(self.db, 'roll_log') or self.db.roll_log is None:
            self.db.roll_log = []
        
        log_entry = {
            'timestamp': datetime.now(),
            'roller': roller,
            'description': description,
            'result': result
        }
        
        self.db.roll_log.append(log_entry)
        # Keep only the last 10 rolls
        if len(self.db.roll_log) > 10:
            self.db.roll_log = self.db.roll_log[-10:]

    def get_roll_log(self):
        """
        Get the roll log for this room.
        
        Returns:
            list: List of roll log entries
        """
        if not hasattr(self.db, 'roll_log') or self.db.roll_log is None:
            self.db.roll_log = []
        return self.db.roll_log

    def get_fae_description(self):
        """Get the fae description of the room."""
        return self.db.fae_desc or "This place has no special fae aspect."

    def set_fae_description(self, description):
        """Set the fae description of the room."""
        self.db.fae_desc = description

class Room(RoomParent):
    pass

