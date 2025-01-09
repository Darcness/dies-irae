from evennia.commands.default.muxcommand import MuxCommand
from evennia.utils.search import search_object
from world.wod20th.models import Stat, SHIFTER_IDENTITY_STATS, SHIFTER_RENOWN, CLAN, MAGE_FACTION, MAGE_SPHERES, \
    TRADITION, TRADITION_SUBFACTION, CONVENTION, METHODOLOGIES, NEPHANDI_FACTION, SEEMING, KITH, SEELIE_LEGACIES, \
    UNSEELIE_LEGACIES, ARTS, REALMS, calculate_willpower, calculate_road
from evennia.utils.ansi import ANSIString
from world.wod20th.utils.damage import format_damage, format_status, format_damage_stacked
from world.wod20th.utils.formatting import format_stat, header, footer, divider
from itertools import zip_longest
from typeclasses.characters import Character

# Define virtue sets for different paths
PATH_VIRTUES = {
    'Humanity': ['Conscience', 'Self-Control', 'Courage'],
    'Night': ['Conviction', 'Instinct', 'Courage'],
    'Metamorphosis': ['Conviction', 'Instinct', 'Courage'],
    'Beast': ['Conviction', 'Instinct', 'Courage'],
    'Harmony': ['Conscience', 'Instinct', 'Courage'],
    'Evil Revelations': ['Conviction', 'Self-Control', 'Courage'],
    'Self-Focus': ['Conviction', 'Instinct', 'Courage'],
    'Scorched Heart': ['Conviction', 'Self-Control', 'Courage'],
    'Entelechy': ['Conviction', 'Self-Control', 'Courage'],
    'Sharia El-Sama': ['Conscience', 'Self-Control', 'Courage'],
    'Asakku': ['Conviction', 'Instinct', 'Courage'],
    'Death and the Soul': ['Conviction', 'Self-Control', 'Courage'],
    'Honorable Accord': ['Conscience', 'Self-Control', 'Courage'],
    'Feral Heart': ['Conviction', 'Instinct', 'Courage'],
    'Orion': ['Conviction', 'Instinct', 'Courage'],
    'Power and the Inner Voice': ['Conviction', 'Instinct', 'Courage'],
    'Lilith': ['Conviction', 'Instinct', 'Courage'],
    'Caine': ['Conviction', 'Instinct', 'Courage'],
    'Cathari': ['Conviction', 'Instinct', 'Courage'],
    'Redemption': ['Conscience', 'Self-Control', 'Courage'],
    'Bones': ['Conviction', 'Self-Control', 'Courage'],
    'Typhon': ['Conviction', 'Self-Control', 'Courage'],
    'Paradox': ['Conviction', 'Self-Control', 'Courage'],
    'Blood': ['Conviction', 'Self-Control', 'Courage'],
    'Hive': ['Conviction', 'Instinct', 'Courage']
}

class CmdSheet(MuxCommand):
    """
    Show a sheet of the character.
    """
    key = "sheet"
    aliases = ["sh"]
    help_category = "Chargen & Character Info"

    def func(self):
        name = self.args.strip()
        if not name:
            name = self.caller.key

        # First try direct name match (with quiet=True to suppress error message)
        chars = self.caller.search(name, global_search=True,
                                 typeclass='typeclasses.characters.Character',
                                 quiet=True)

        # Handle if search returns a list
        character = chars[0] if isinstance(chars, list) else chars

        # If no direct match, try alias
        if not character:
            character = Character.get_by_alias(name.lower())

        if character:
            # If not builder, verify character is in same location
            if not self.caller.check_permstring("builders"):
                if character != self.caller and character not in self.caller.location.contents:
                    self.caller.msg(f"You can't see {name} here.")
                    return
        else:
            self.caller.msg(f"Character '{name}' not found.")
            return

        # Modify permission check - allow builders/admins to view any sheet
        if not self.caller.check_permstring("builders"):
            if self.caller != character:
                self.caller.msg(f"|rYou can't see the sheet of {character.key}.|n")
                return

        # Check if character has stats and splat initialized
        if not character.db.stats or not character.db.stats.get('other', {}).get('splat', {}).get('Splat', {}).get('perm'):
            self.caller.msg("|rYou must set a splat to initialize your sheet. Use +selfstat splat=<Splat> or ask staff to set it.|n")
            return

        try:
            splat = character.get_stat('other', 'splat', 'Splat')
        except AttributeError:
            self.caller.msg("|rError accessing character stats. Please contact staff.|n")
            return

        if not splat:
            splat = "Mortal"

        stats = character.db.stats
        if not stats:
            character.db.stats = {}

        string = header(f"Character Sheet for:|n {character.get_display_name(self.caller)}")

        string += header("Identity", width=78, color="|y")

        common_stats = ['Full Name', 'Date of Birth', 'Concept']
        splat = character.db.stats.get('other', {}).get('splat', {}).get('Splat', {}).get('perm', '')

        if splat.lower() == 'changeling':
            common_stats += ['Seelie Legacy', 'Unseelie Legacy']
        else:
            common_stats += ['Nature', 'Demeanor']

        if splat.lower() == 'vampire':
            splat_specific_stats = ['Clan', 'Date of Embrace', 'Generation', 'Sire', 'Enlightenment']
        elif splat.lower() == 'shifter':
            shifter_type = character.db.stats.get('identity', {}).get('lineage', {}).get('Type', {}).get('perm', '')
            splat_specific_stats = ['Type', 'Deed Name', 'Rank']
            
            # Add type-specific stats from the SHIFTER_IDENTITY_STATS dictionary
            if shifter_type:
                type_specific_stats = SHIFTER_IDENTITY_STATS.get(shifter_type, [])
                splat_specific_stats.extend(type_specific_stats)
                
                # Add Camp/Lodge for Garou characters based on tribe
                if shifter_type.lower() == 'garou':
                    # Check if the character is a Silver Fang
                    tribe = character.db.stats.get('identity', {}).get('lineage', {}).get('Tribe', {}).get('perm', '')
                    if tribe.lower() == 'silver fangs':
                        splat_specific_stats.extend(['Lodge', 'Fang House'])
                    else:
                        # Only add Camp if it has a value
                        camp = character.db.stats.get('identity', {}).get('lineage', {}).get('Camp', {}).get('perm', '')
                        if camp:
                            splat_specific_stats.append('Camp')
        elif splat.lower() == 'mage':
            mage_faction = character.db.stats.get('identity', {}).get('lineage', {}).get('Mage Faction', {}).get('perm', '')
            splat_specific_stats = ['Essence', 'Mage Faction']

            if mage_faction.lower() == 'traditions':
                traditions = character.db.stats.get('identity', {}).get('lineage', {}).get('Tradition', {}).get('perm', '')
                splat_specific_stats.extend(['Tradition'])
                if traditions:
                        splat_specific_stats.append('Traditions Subfaction')
            elif mage_faction.lower() == 'technocracy':
                splat_specific_stats.extend(['Convention', 'Methodology'])
            elif mage_faction.lower() == 'nephandi':
                splat_specific_stats.append('Nephandi Faction')
        elif splat.lower() == 'changeling':
            splat_specific_stats = ['Kith', 'Seeming', 'House']
        else:
            splat_specific_stats = []

        all_stats = []
        # Add common stats first
        for stat in common_stats:
            if stat not in all_stats:
                all_stats.append(stat)

        # Add splat-specific stats
        for stat in splat_specific_stats:
            if stat not in all_stats:
                all_stats.append(stat)

        # Add Splat at the end if not already included
        if 'Splat' not in all_stats:
            all_stats.append('Splat')

        def format_stat_with_dots(stat, value, width=38):
            display_stat = 'Subfaction' if stat == 'Traditions Subfaction' else stat
            stat_str = f" {display_stat}"
            
            # Handle empty/None values
            if value is None or value == '':
                if stat == 'Rank':  # Special case for Rank
                    value_str = '0'
                else:
                    value_str = ''
            else:
                value_str = str(value)
            
            dots = "." * (width - len(stat_str) - len(value_str) - 1)
            return f"{stat_str}{dots}{value_str}"

        for i in range(0, len(all_stats), 2):
            left_stat = all_stats[i]
            right_stat = all_stats[i+1] if i+1 < len(all_stats) else None

            left_value = character.db.stats.get('identity', {}).get('personal', {}).get(left_stat, {}).get('perm', '')
            if not left_value:
                left_value = character.db.stats.get('identity', {}).get('lineage', {}).get(left_stat, {}).get('perm', '')
                # Special handling for Rank
                if left_stat == 'Rank' and left_value == '':
                    left_value = '0'
            if not left_value:
                left_value = character.db.stats.get('identity', {}).get('other', {}).get(left_stat, {}).get('perm', '')
            if not left_value and left_stat == 'Splat':
                left_value = character.db.stats.get('other', {}).get('splat', {}).get('Splat', {}).get('perm', '')
            # New code for Nature and Demeanor
            if left_stat == 'Nature':
                left_value = character.db.stats.get('archetype', {}).get('personal', {}).get('Nature', {}).get('perm', '')
            elif left_stat == 'Demeanor':
                left_value = character.db.stats.get('archetype', {}).get('personal', {}).get('Demeanor', {}).get('perm', '')

            left_formatted = format_stat_with_dots(left_stat, left_value)

            if right_stat:
                right_value = character.db.stats.get('identity', {}).get('personal', {}).get(right_stat, {}).get('perm', '')
                if not right_value:
                    right_value = character.db.stats.get('identity', {}).get('lineage', {}).get(right_stat, {}).get('perm', '')
                if not right_value:
                    right_value = character.db.stats.get('identity', {}).get('other', {}).get(right_stat, {}).get('perm', '')
                if not right_value and right_stat == 'Splat':
                    right_value = character.db.stats.get('other', {}).get('splat', {}).get('Splat', {}).get('perm', '')
                # New code for Nature and Demeanor
                if right_stat == 'Nature':
                    right_value = character.db.stats.get('archetype', {}).get('personal', {}).get('Nature', {}).get('perm', '')
                elif right_stat == 'Demeanor':
                    right_value = character.db.stats.get('archetype', {}).get('personal', {}).get('Demeanor', {}).get('perm', '')

                right_formatted = format_stat_with_dots(right_stat, right_value)
                string += f"{left_formatted}  {right_formatted}\n"
            else:
                string += f"{left_formatted}\n"

        string += header("Attributes", width=78, color="|y")
        string += " " + divider("Physical", width=25, fillchar=" ") + " "
        string += divider("Social", width=25, fillchar=" ") + " "
        string += divider("Mental", width=25, fillchar=" ") + "\n"

        # Function to add padding to social and mental attributes
        def pad_attribute(attr):
            return " " * 1 + attr.ljust(22)
        string += format_stat("Strength", character.get_stat('attributes', 'physical', 'Strength'), default=1, tempvalue=character.get_stat('attributes', 'physical', 'Strength', temp=True)) + " "
        string += format_stat("Charisma", character.get_stat('attributes', 'social', 'Charisma'), default=1, tempvalue=character.get_stat('attributes', 'social', 'Charisma', temp=True)) + " "
        string += pad_attribute(format_stat("Perception", character.get_stat('attributes', 'mental', 'Perception'), default=1, tempvalue=character.get_stat('attributes', 'mental', 'Perception', temp=True))) + "\n"
        string += format_stat("Dexterity", character.get_stat('attributes', 'physical', 'Dexterity'), default=1, tempvalue=character.get_stat('attributes', 'physical', 'Dexterity', temp=True)) + " "
        string += format_stat("Manipulation", character.get_stat('attributes', 'social', 'Manipulation'), default=1, tempvalue=character.get_stat('attributes', 'social', 'Manipulation', temp=True)) + " "
        string += pad_attribute(format_stat("Intelligence", character.get_stat('attributes', 'mental', 'Intelligence'), default=1, tempvalue=character.get_stat('attributes', 'mental', 'Intelligence', temp=True))) + "\n"
        string += format_stat("Stamina", character.get_stat('attributes', 'physical', 'Stamina'), default=1, tempvalue=character.get_stat('attributes', 'physical', 'Stamina', temp=True)) + " "

        # Special handling for Appearance
        appearance_value = character.get_stat('attributes', 'social', 'Appearance', temp=False)
        appearance_temp = character.get_stat('attributes', 'social', 'Appearance', temp=True)

        # Check if character is a vampire with a clan that should have 0 Appearance
        zero_appearance_clans = ['nosferatu', 'samedi']
        clan = character.db.stats.get('identity', {}).get('lineage', {}).get('Clan', {}).get('perm', '').lower()
        is_zero_appearance_clan = clan in zero_appearance_clans

        # Check if character is in a form that should have 0 Appearance
        current_form = character.db.current_form
        zero_appearance_forms = ['crinos', 'anthros', 'arthren', 'sokto', 'chatro']
        is_zero_appearance_form = current_form and current_form.lower() in zero_appearance_forms

        if is_zero_appearance_clan or is_zero_appearance_form:
            string += format_stat("Appearance", 0, default=0, tempvalue=0, allow_zero=True) + " "
        else:
            string += format_stat("Appearance", appearance_value, default=1, tempvalue=appearance_temp) + " "

        string += pad_attribute(format_stat("Wits", character.get_stat('attributes', 'mental', 'Wits'), default=1, tempvalue=character.get_stat('attributes', 'mental', 'Wits', temp=True))) + "\n"

        string += header("Abilities", width=78, color="|y")
        string += " " + divider("Talents", width=25, fillchar=" ") + " "
        string += divider("Skills", width=25, fillchar=" ") + " "
        string += divider("Knowledges", width=25, fillchar=" ") + "\n"


        def get_abilities_for_splat(character, stat_type):
            """Helper function to get abilities for a specific splat and stat type"""
            splat = character.db.stats.get('other', {}).get('splat', {}).get('Splat', {}).get('perm', '')
            shifter_type = character.db.stats.get('identity', {}).get('lineage', {}).get('Type', {}).get('perm', '')
            clan = character.db.stats.get('identity', {}).get('lineage', {}).get('Clan', {}).get('perm', '')

            # Define base abilities for each category
            BASE_ABILITIES = {
                'talent': ['Alertness', 'Athletics', 'Awareness', 'Brawl', 'Empathy', 
                          'Expression', 'Intimidation', 'Leadership', 'Streetwise', 'Subterfuge'],
                'skill': ['Animal Ken', 'Crafts', 'Drive', 'Etiquette', 'Firearms', 
                         'Larceny', 'Melee', 'Performance', 'Stealth', 'Survival', 'Technology'],
                'knowledge': ['Academics', 'Computer', 'Cosmology', 'Enigmas', 'Finance', 'Investigation', 
                            'Law', 'Medicine', 'Occult', 'Politics', 'Science']
            }
            
            # Get base abilities first
            abilities = list(Stat.objects.filter(
                category='abilities',
                stat_type=stat_type,
                name__in=BASE_ABILITIES[stat_type]
            ))
            
            # Add splat-specific abilities
            if splat == 'Shifter':
                if stat_type == 'talent':
                    # Add Primal-Urge for all shifters
                    primal_urge = Stat.objects.filter(name='Primal-Urge').first()
                    if primal_urge:
                        # Insert Primal-Urge in alphabetical order
                        insert_index = next((i for i, ability in enumerate(abilities) 
                                           if ability.name > 'Primal-Urge'), len(abilities))
                        abilities.insert(insert_index, primal_urge)
                    
                    # Add Flight ONLY for specific shifter types
                    if shifter_type and shifter_type.strip() in ['Corax', 'Camazotz', 'Mokole']:
                        flight = Stat.objects.filter(name='Flight').first()
                        if flight:
                            # Insert Flight in alphabetical order
                            insert_index = next((i for i, ability in enumerate(abilities) 
                                               if ability.name > 'Flight'), len(abilities))
                            abilities.insert(insert_index, flight)
                
                elif stat_type == 'knowledge':
                    # Add Rituals for all shifters
                    rituals = Stat.objects.filter(name='Rituals').first()
                    if rituals:
                        # Insert Rituals in alphabetical order
                        insert_index = next((i for i, ability in enumerate(abilities) 
                                           if ability.name > 'Rituals'), len(abilities))
                        abilities.insert(insert_index, rituals)
            
            # Add Flight for Gargoyle vampires
            elif splat == 'Vampire' and clan and clan.strip() == 'Gargoyle' and stat_type == 'talent':
                flight = Stat.objects.filter(name='Flight').first()
                if flight:
                    # Insert Flight in alphabetical order
                    insert_index = next((i for i, ability in enumerate(abilities) 
                                       if ability.name > 'Flight'), len(abilities))
                    abilities.insert(insert_index, flight)

            return abilities

        talents = get_abilities_for_splat(character, 'talent')
        skills = get_abilities_for_splat(character, 'skill')
        knowledges = get_abilities_for_splat(character, 'knowledge')

        # Function to format abilities with padding for skills and knowledges
        def format_ability(ability, category):
            formatted = format_stat(ability.name, character.get_stat(ability.category, ability.stat_type, ability.name), default=0)
            if category in ['knowledge']:
                return " " * 1 + formatted.ljust(22)
            return formatted.ljust(25)

        formatted_talents = [format_ability(talent, 'talent') for talent in talents]
        formatted_skills = [format_ability(skill, 'skill') for skill in skills]
        formatted_knowledges = [format_ability(knowledge, 'knowledge') for knowledge in knowledges]

        # Add specialties
        ability_lists = [
            (formatted_talents, talents, 'talent'),
            (formatted_skills, skills, 'skill'),
            (formatted_knowledges, knowledges, 'knowledge')
        ]

        for formatted_list, ability_list, ability_type in ability_lists:
            for ability in ability_list:
                if character.db.specialties and ability.name in character.db.specialties:
                    for specialty in character.db.specialties[ability.name]:
                        formatted_specialty = format_ability(Stat(name=f"`{specialty}"), ability_type)
                        formatted_list.append(formatted_specialty)

        # For primary abilities
        max_len = max(len(formatted_talents), len(formatted_skills), len(formatted_knowledges))
        formatted_talents.extend([" " * 25] * (max_len - len(formatted_talents)))
        formatted_skills.extend([" " * 25] * (max_len - len(formatted_skills)))
        formatted_knowledges.extend([" " * 25] * (max_len - len(formatted_knowledges)))

        for talent, skill, knowledge in zip(formatted_talents, formatted_skills, formatted_knowledges):
            string += f"{talent}{skill}{knowledge}\n"

        # Add splat-specific abilities
        abilities = character.db.stats.get('abilities', {})
        if 'ability' in abilities:
            for ability_name, values in abilities['ability'].items():
                if values.get('perm') is not None and character.can_have_ability(ability_name):
                    # Add to appropriate section based on the ability's category
                    if ability_name == "Flight":  # Add under Talents
                        string += format_stat(ability_name, values['perm'], width=25) + "\n"

        string += header("Secondary Abilities", width=78, color="|y")
        string += " " + divider("Talents", width=25, fillchar=" ") + " "
        string += divider("Skills", width=25, fillchar=" ") + " "
        string += divider("Knowledges", width=25, fillchar=" ") + "\n"

        # Get splat-specific secondary abilities
        splat = character.db.stats.get('other', {}).get('splat', {}).get('Splat', {}).get('perm', '')

        # Function to format abilities with padding for skills and knowledges
        def format_secondary_ability(ability_name, category):
            value = character.get_stat('secondary_abilities', category, ability_name)
            formatted = format_stat(ability_name, value, default=0)
            if category in ['secondary_knowledge']:
                return " " * 1 + formatted.ljust(22)
            return formatted.ljust(25)

        # Initialize empty lists for each category
        formatted_secondary_talents = []
        formatted_secondary_skills = []
        formatted_secondary_knowledges = []

        # Base secondary abilities for all characters
        base_secondary_talents = ['Carousing', 'Diplomacy', 'Intrigue', 'Mimicry', 'Scrounging', 'Seduction', 'Style']
        base_secondary_skills = ['Archery', 'Fortune-Telling', 'Fencing', 'Gambling', 'Jury-Rigging', 'Pilot', 'Torture']
        base_secondary_knowledges = ['Area Knowledge', 'Cultural Savvy', 'Demolitions', 'Herbalism', 'Media', 'Power-Brokering', 'Vice']

        # Add base secondary abilities for all characters
        formatted_secondary_talents.extend([
            format_secondary_ability(talent, 'secondary_talent')
            for talent in base_secondary_talents
        ])
        formatted_secondary_skills.extend([
            format_secondary_ability(skill, 'secondary_skill')
            for skill in base_secondary_skills
        ])
        formatted_secondary_knowledges.extend([
            format_secondary_ability(knowledge, 'secondary_knowledge')
            for knowledge in base_secondary_knowledges
        ])

        # If character is a Mage, add Mage-specific secondary abilities
        if splat.lower() == 'mage':
            # Secondary Talents
            mage_secondary_talents = ['High Ritual', 'Blatancy']
            formatted_secondary_talents.extend([
                format_secondary_ability(talent, 'secondary_talent')
                for talent in mage_secondary_talents
            ])

            # Secondary Skills
            mage_secondary_skills = ['Microgravity Ops', 'Energy Weapons', 'Helmsman', 'Biotech']
            formatted_secondary_skills.extend([
                format_secondary_ability(skill, 'secondary_skill')
                for skill in mage_secondary_skills
            ])

            # Secondary Knowledges
            mage_secondary_knowledges = ['Hypertech', 'Cybernetics', 'Paraphysics', 'Xenobiology']
            formatted_secondary_knowledges.extend([
                format_secondary_ability(knowledge, 'secondary_knowledge')
                for knowledge in mage_secondary_knowledges
            ])

        # For secondary abilities
        max_len = max(
            len(formatted_secondary_talents),
            len(formatted_secondary_skills),
            len(formatted_secondary_knowledges)
        )

        # Pad the lists with actual spaces instead of empty strings
        formatted_secondary_talents.extend([" " * 25] * (max_len - len(formatted_secondary_talents)))
        formatted_secondary_skills.extend([" " * 25] * (max_len - len(formatted_secondary_skills)))
        formatted_secondary_knowledges.extend([" " * 25] * (max_len - len(formatted_secondary_knowledges)))

        # Display the secondary abilities in columns
        for talent, skill, knowledge in zip(formatted_secondary_talents, formatted_secondary_skills, formatted_secondary_knowledges):
            string += f"{talent}{skill}{knowledge}\n"

        # Process powers and advantages in two columns
        string += header("Advantages", width=78, color="|y")
        
        powers = []
        left_column = []

        # Process powers based on character splat (right column)
        character_splat = character.db.stats.get('other', {}).get('splat', {}).get('Splat', {}).get('perm', '')
        if character_splat == 'Mage':
            powers.append(divider("Spheres", width=38, color="|b"))
            spheres = ['Correspondence', 'Entropy', 'Forces', 'Life', 'Matter', 'Mind', 'Prime', 'Spirit', 'Time', 'Data', 'Primal Utility', 'Dimensional Science']
            for sphere in spheres:
                sphere_value = character.db.stats.get('powers', {}).get('sphere', {}).get(sphere, {}).get('perm', 0)
                powers.append(format_stat(sphere, sphere_value, default=0, width=38))
        elif character_splat == 'Vampire':
            # Vampire-specific powers section
            powers.append(divider("Disciplines", width=38, color="|b"))
            disciplines = character.db.stats.get('powers', {}).get('discipline', {})
            for discipline, values in disciplines.items():
                discipline_value = values.get('perm', 0)
                powers.append(format_stat(discipline, discipline_value, default=0, width=38))
            
            # Combo Disciplines
            combo_disciplines = character.db.stats.get('powers', {}).get('combodisc', {})
            if combo_disciplines:
                powers.append(divider("Combo Disciplines", width=38, color="|b"))
                for combo, values in combo_disciplines.items():
                    combo_value = values.get('perm', 0)
                    powers.append(format_stat(combo, combo_value, default=0, width=38))
        elif character_splat == 'Changeling':
            powers.append(divider("Arts", width=38, color="|b"))
            arts = character.db.stats.get('powers', {}).get('art', {})
            for art, values in arts.items():
                art_value = values.get('perm', 0)
                powers.append(format_stat(art, art_value, default=0, width=38))
            powers.append(divider("Realms", width=38, color="|b"))
            realms = character.db.stats.get('powers', {}).get('realm', {})
            for realm, values in realms.items():
                realm_value = values.get('perm', 0)
                powers.append(format_stat(realm, realm_value, default=0, width=38))
        elif character_splat == 'Shifter':
            powers.append(divider("Gifts", width=38, color="|b"))
            gifts = character.db.stats.get('powers', {}).get('gift', {})
            for gift, values in gifts.items():
                gift_value = values.get('perm', 0)
                powers.append(format_stat(gift, gift_value, default=0, width=38))

            powers.append(divider("Rites", width=38, color="|b"))
            rites = character.db.stats.get('powers', {}).get('rite', {})
            for rite, values in rites.items():
                rite_value = values.get('perm', 0)
                powers.append(format_stat(rite, rite_value, default=0, width=38))

        # Build left column (backgrounds + merits & flaws)
        left_column.append(divider("Backgrounds", width=38, color="|b"))
        char_backgrounds = character.db.stats.get('backgrounds', {}).get('background', {})
        for background, values in char_backgrounds.items():
            background_value = values.get('perm', 0)
            left_column.append(format_stat(background, background_value, width=38))

        # Add a blank line between sections
        left_column.append(" " * 38)

        # Separate Merits section with consistent dot width
        left_column.append(divider("Merits", width=38, color="|b"))
        merits = character.db.stats.get('merits', {})
        for merit_type, merit_dict in merits.items():
            for merit, values in merit_dict.items():
                merit_value = values.get('perm', 0)
                # Use the same width=38 as backgrounds
                left_column.append(format_stat(merit, merit_value, width=38))

        # Add a blank line between Merits and Flaws
        left_column.append(" " * 38)

        # Separate Flaws section with consistent dot width
        left_column.append(divider("Flaws", width=38, color="|b"))
        flaws = character.db.stats.get('flaws', {})
        for flaw_type, flaw_dict in flaws.items():
            for flaw, values in flaw_dict.items():
                flaw_value = values.get('perm', 0)
                # Use the same width=38 as backgrounds
                left_column.append(format_stat(flaw, flaw_value, width=38))

        # Ensure both columns have the same number of rows
        max_len = max(len(powers), len(left_column))
        powers.extend([""] * (max_len - len(powers)))
        left_column.extend([""] * (max_len - len(left_column)))

        # Combine columns with new widths (38+38 = 76 total width with 2 spaces between)
        for left, power in zip(left_column, powers):
            string += f"{left.strip().ljust(38)}  {power.strip().ljust(38)}\n"

        # Display Pools, Virtues & Health in the same three-column format
        string += header("Pools, Virtues & Status", width=78, color="|y")

        pools_list = []
        virtues_list = []
        status_list = []

        # Add headers with adjusted positioning
        pools_list.append(divider("Pools", width=25, fillchar=" "))
        virtues_list.append(divider("Virtues", width=25, fillchar=" "))
        status_list.append(divider("Health & Status", width=25, fillchar=" "))

        # Add health status to status_list without extra padding
        health_status = format_damage_stacked(character)
        status_list.extend(health_status)

        # Process pools based on splat
        if splat.lower() == 'vampire':
            # Get generation for blood pool calculation
            generation = character.db.stats.get('identity', {}).get('lineage', {}).get('Generation', {}).get('perm', '13th')
            max_blood = calculate_blood_pool(generation)
            
            pools_list.append(format_stat('Blood Pool', f"{format_pool_value(character, 'Blood')}/{max_blood}", width=25))
            pools_list.append(format_stat('Willpower', format_pool_value(character, 'Willpower'), width=25))
            
        elif splat.lower() == 'shifter':
            pools_list.append(format_stat('Rage', format_pool_value(character, 'Rage'), width=25))
            pools_list.append(format_stat('Gnosis', format_pool_value(character, 'Gnosis'), width=25))
            pools_list.append(format_stat('Willpower', format_pool_value(character, 'Willpower'), width=25))
            
        elif splat.lower() == 'mage':
            pools_list.append(format_stat('Arete', format_pool_value(character, 'Arete'), width=25))
            pools_list.append(format_stat('Quintessence', format_pool_value(character, 'Quintessence'), width=25))
            pools_list.append(format_stat('Willpower', format_pool_value(character, 'Willpower'), width=25))
            
        elif splat.lower() == 'changeling':
            pools_list.append(format_stat('Glamour', format_pool_value(character, 'Glamour'), width=25))
            pools_list.append(format_stat('Banality', format_pool_value(character, 'Banality'), width=25))
            pools_list.append(format_stat('Willpower', format_pool_value(character, 'Willpower'), width=25))
        else:
            # Default/Mortal
            pools_list.append(format_stat('Willpower', format_pool_value(character, 'Willpower'), width=25))

        # Handle virtues with adjusted positioning
        if splat.lower() == 'shifter':
            shifter_type = character.get_stat('identity', 'lineage', 'Type')
            if shifter_type in SHIFTER_RENOWN:
                for renown in SHIFTER_RENOWN[shifter_type]:
                    renown_value = character.get_stat('advantages', 'renown', renown, temp=False) or 0
                    dots = "." * (19 - len(renown))
                    virtues_list.append(f" {renown}{dots}{renown_value}".ljust(25))
            else:
                default_renown = ['Glory', 'Honor', 'Wisdom']
                for renown in default_renown:
                    renown_value = character.get_stat('virtues', 'moral', renown, temp=False) or 0
                    dots = "." * (19 - len(renown))
                    virtues_list.append(f" {renown}{dots}{renown_value}".ljust(25))
        else:
            # Handle other splat virtues
            virtues = character.db.stats.get('virtues', {}).get('moral', {})
            path = character.get_stat('identity', 'personal', 'Enlightenment')
            path_virtues = PATH_VIRTUES.get(path, ['Conscience', 'Self-Control', 'Courage'])
            
            # Add Road/Path rating first for vampires
            if splat.lower() == 'vampire':
                road_value = character.get_stat('pools', 'moral', 'Road') or 0
                dots = "." * (19 - len("Road"))
                virtues_list.append(f" Road{dots}{road_value}".ljust(25))
            
            for virtue in path_virtues:
                virtue_value = virtues.get(virtue, {}).get('perm', 0)
                dots = "." * (19 - len(virtue))
                virtues_list.append(f" {virtue}{dots}{virtue_value}".ljust(25))

        # Ensure all columns have the same number of rows
        max_len = max(len(pools_list), len(virtues_list), len(status_list))
        pools_list.extend(["".ljust(25)] * (max_len - len(pools_list)))
        virtues_list.extend(["".ljust(25)] * (max_len - len(virtues_list)))
        status_list.extend(["".ljust(25)] * (max_len - len(status_list)))

        # Display the pools, virtues and status in columns with adjusted spacing
        for pool, virtue, status in zip(pools_list, virtues_list, status_list):
            # Use fixed widths for each column and add consistent spacing
            string += f"{pool:<25}  {virtue:>25}  {status}\n"

        # Check approval status and add it at the end
        if character.db.approved:
            string += header("Approved Character", width=78, fillchar="-")
        else:
            string += header("Unapproved Character", width=78, fillchar="-")

        # Send the complete sheet to the caller
        self.caller.msg(string)

def format_pool_value(character, pool_name):
    """Format a pool value with both permanent and temporary values."""
    perm = character.get_stat('pools', 'dual', pool_name, temp=False)
    temp = character.get_stat('pools', 'dual', pool_name, temp=True)

    if perm is None:
        perm = 0
    if temp is None:
        temp = perm

    return f"{perm}({temp})" if temp != perm else str(perm)

def calculate_blood_pool(generation):
    """
    Calculate blood pool based on vampire generation.
    
    Args:
        generation (str): Character's generation (e.g. '7th', '13th')
        
    Returns:
        int: Maximum blood pool for that generation
    """
    # Extract number from generation string and convert to int
    try:
        gen_num = int(''.join(filter(str.isdigit, str(generation))))
    except (ValueError, TypeError):
        gen_num = 13  # Default to 13th generation if invalid/missing

    # Calculate blood pool based on generation
    if gen_num >= 13:
        return 10
    elif gen_num == 12:
        return 11
    elif gen_num == 11:
        return 12
    elif gen_num == 10:
        return 13
    elif gen_num == 9:
        return 14
    elif gen_num == 8:
        return 15
    elif gen_num == 7:
        return 20
    else:
        return 10  # Default to 10 for any unexpected values