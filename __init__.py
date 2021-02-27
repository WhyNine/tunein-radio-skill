from mycroft import MycroftSkill
from mycroft.util.log import getLogger
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel
from mycroft.skills.audioservice import AudioService
from mycroft.util.parse import match_one
from xml.dom.minidom import parseString
import requests
import sys

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
            LOGGER.debug("Set vlc as backend to be used")
        
    def CPS_match_query_phrase(self, phrase):
        alias = False
        if phrase in self.aliases.keys():
            LOGGER.info(f"Using alias {self.aliases[phrase]}")
            phrase = self.aliases[phrase]
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
        LOGGER.debug(f'Match level {confidence} for {stations[match]["name"]}')
        if (not alias) and ("radio" not in phrase):
            r_match, r_confidence = match_one(r_phrase, matches)
            LOGGER.debug(f'Match level {r_confidence} for {stations[r_match]["name"]}')
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
        LOGGER.info(f"About to play {name} from \n{url}")
        self.speak_dialog('start', data={"station": name}, wait=True)
        self.stop()
        self.CPS_play(url, utterance=self.backend)

    def on_settings_changed(self):
        self.get_settings()

    def get_settings(self):
        self.aliases = {}
        for i in range(1, 6):
            name = self.settings.get(f'name{i}', "")
            alias = self.settings.get(f'alias{i}', "")
            if (len(name) > 1) and (len(alias) > 1):
                self.aliases[alias] = name


def create_skill():
    return TuneinRadio()
