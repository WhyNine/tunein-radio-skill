from mycroft import MycroftSkill, intent_file_handler


class TuneinRadio(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('radio.tunein.intent')
    def handle_radio_tunein(self, message):
        self.speak_dialog('radio.tunein')


def create_skill():
    return TuneinRadio()

