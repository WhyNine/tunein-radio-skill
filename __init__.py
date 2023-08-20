from mycroft import MycroftSkill
from mycroft.util.log import getLogger
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.skills.audioservice import AudioService
from mycroft.util.parse import match_one
from mycroft.messagebus.message import Message
from xml.dom.minidom import parseString
import requests
import re

LOGGER = getLogger(__name__)
BASE_URL = "http://opml.radiotime.com/Search.ashx"

class TuneinRadio(CommonPlaySkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    def initialize(self):
        self.settings_change_callback = self.on_settings_changed
        self.get_settings()
        self.audio = AudioService(self.bus)
        self.spoken_name = "Tune In Radio"
        backends = self.audio.available_backends()
        self.backend = {}
        if "vlc" in backends.keys():
            self.backend["vlc"] = backends["vlc"]
            self.backend["vlc"]["normal_volume"] = 70
            self.backend["vlc"]["duck_volume"] = 5
            LOGGER.debug("Set vlc as backend to be used")
        self.regexes = {}

    # Get the correct localised regex
    def translate_regex(self, regex):
        if regex not in self.regexes:
            path = self.find_resource(regex + '.regex')
            if path:
                with open(path) as f:
                    string = f.read().strip()
                self.regexes[regex] = string
        return self.regexes[regex]

    def CPS_match_query_phrase(self, phrase):
        for regex in ['internet_radio_on_tunein', 'on_tunein', 'internet_radio']:
            match = re.search(self.translate_regex(regex), phrase)
            if match:
                data = re.sub(self.translate_regex(regex), '', phrase)
                LOGGER.debug(f"Found '{data}' with '{regex} in '{phrase}'")
                phrase = data
                break
        alias = False
        if phrase in self.aliases.keys():
            LOGGER.info(f"Using alias {self.aliases[phrase]}")
            phrase = self.aliases[phrase].lower()
            alias = True
        res = requests.get(f"{BASE_URL}?query={phrase}")
        dom = parseString(res.text)
        entries = dom.getElementsByTagName("outline")
        station_url = ""
        station_name = ""
        matches = {}
        stations = {}
        for entry in entries:
            if (entry.getAttribute("type") == "audio") and (entry.getAttribute("item") == "station") and (entry.getAttribute("key") != "unavailable"):
                station_url = entry.getAttribute("URL")
                station_name = entry.getAttribute("text")
                LOGGER.debug(f"{station_name}: {station_url}\n")
                stations[station_name] = {"url": station_url, "name": station_name}
                matches[station_name.lower()] = station_name
        if (station_name == ""):
            return None
        r_confidence = 0
        r_phrase = phrase + " radio"
        match, confidence = match_one(phrase, matches)
        LOGGER.info(f'Match level {confidence} for {stations[match]["name"]}')
        if (not alias) and ("radio" not in phrase):
            r_match, r_confidence = match_one(r_phrase, matches)
            LOGGER.info(f'Match level {r_confidence} for {stations[r_match]["name"]}')
        if confidence == 1:
            return (phrase, CPSMatchLevel.EXACT, stations[match])
        if r_confidence == 1:
            return (r_phrase, CPSMatchLevel.EXACT, stations[r_match])
        if confidence > 0.8:
            return (phrase, CPSMatchLevel.MULTI_KEY, stations[match])
        if r_confidence > 0.8:
            return (r_phrase, CPSMatchLevel.MULTI_KEY, stations[r_match])
        if confidence > 0.6:
            return (phrase, CPSMatchLevel.TITLE, stations[match])
        if r_confidence > 0.6:
            return (r_phrase, CPSMatchLevel.TITLE, stations[r_match])
        return None

    def CPS_start(self, phrase, data):
        url = data["url"]
        name = data["name"]
        self.stop()
        self.speak_dialog('start', data={"station": name}, wait=True)
        LOGGER.info(f"About to play {name} from \n{url}")
        self.CPS_play(url, utterance=self.backend)

    def on_settings_changed(self):
        self.get_settings()

    def get_settings(self):
        self.aliases = {}
        for i in range(1, 6):
            name = self.settings.get(f'name{i}', "")
            alias = self.settings.get(f'alias{i}', "").lower()
            if (len(name) > 1) and (len(alias) > 1):
                self.aliases[alias] = name


def create_skill():
    return TuneinRadio()
