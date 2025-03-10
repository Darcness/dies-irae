from evennia.commands.default.muxcommand import MuxCommand
from commands.CmdPose import PoseBreakMixin

class CmdSay(PoseBreakMixin, MuxCommand):
    """
    speak as your character

    Usage:
      say <message>
      say ~<message>     (to speak in your set language)
      "<message>
      '~<message>    (to speak in your set language)

    Talk to those in your current location.
    """

    key = "say"
    aliases = ['"', "'"]
    locks = "cmd:all()"
    help_category = "General"
    arg_regex = r""

    def func(self):
        """
        This is where the language handling happens.
        """
        caller = self.caller

        if not self.args:
            caller.msg("Say what?")
            return

        speech = self.args

        # Handle the case where the alias " or ' is used
        if self.cmdstring in ['"', "'"]:
            speech = speech
        else:
            # For the 'say' command, we need to preserve leading whitespace
            # to differentiate between 'say ~message' and 'say ~ message'
            speech = speech.rstrip()

        # Send pose break before the message
        self.send_pose_break()

        # Prepare the say messages
        msg_self, msg_understand, msg_not_understand, language = caller.prepare_say(speech)

        # Filter receivers based on Umbra state
        filtered_receivers = [
            obj for obj in caller.location.contents
            if obj.has_account and obj.db.in_umbra == caller.db.in_umbra
        ]

        # Send messages to receivers
        for receiver in filtered_receivers:
            if receiver != caller:
                # Check for Universal Language merit
                has_universal = any(
                    merit.lower().replace(' ', '') == 'universallanguage'
                    for category in receiver.db.stats.get('merits', {}).values()
                    for merit in category.keys()
                )

                # Get the languages the receiver knows
                receiver_languages = receiver.get_languages()

                # If they have Universal Language, know the language, or it's not a language-tagged message
                if has_universal or not language or (language and language in receiver_languages):
                    receiver.msg(msg_understand)
                else:
                    receiver.msg(msg_not_understand)
            else:
                # The speaker always understands their own speech
                receiver.msg(msg_self)
