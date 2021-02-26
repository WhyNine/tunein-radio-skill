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
        backends = self.audio.available_backends()
        self.backend = {}
        if "vlc" in backends.keys():
            self.backend["vlc"] = backends["vlc"]
            LOGGER.info("Set vlc as backend to be used")
        
    def CPS_match_query_phrase(self, phrase):
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
                LOGGER.info(f"{station_name}: {station_url}\n")
                stations[station_name] = {"url": station_url, "name": station_name}
                matches[station_name.lower()] = station_name
        if (station_name == ""):
            return None
        r_confidence = 0
        match, confidence = match_one(phrase, matches)
        LOGGER.info(f'Match level {confidence} for {stations[match]["name"]}')
        if "radio" not in phrase:
            r_match, r_confidence = match_one(phrase + " radio", matches)
            LOGGER.info(f'Match level {r_confidence} for {stations[r_match]["name"]}')
        if confidence == 1:
            return (match, CPSMatchLevel.EXACT, match)
        if r_confidence == 1:
            return (r_match, CPSMatchLevel.EXACT, r_match)
        if confidence > 0.8:
            return (match, CPSMatchLevel.MULTI_KEY, match)
        if r_confidence > 0.8:
            return (r_match, CPSMatchLevel.MULTI_KEY, r_match)
        if confidence > 0.6:
            return (match, CPSMatchLevel.TITLE, match)
        if r_confidence > 0.6:
            return (r_match, CPSMatchLevel.TITLE, r_match)
        return None

    def CPS_start(self, phrase, data):
        url = data["url"]
        name = data["name"]
        LOGGER.info(f"About to play {name}")
        self.speak_dialog('start', data={"station": name}, wait=False)
        self.stop()
        self.CPS_play(url, utterance=self.backend)
        LOGGER.info(f"Playing from \n{url}")


    def on_settings_changed(self):
        self.get_settings()

    def get_settings(self):
        self.channels = {}
        names = []
        aliases = []
        for i in range(1, 6):
            name = self.settings.get(f'name{i}', "")
            alias = self.settings.get(f'alias{i}', "")
            if (len(name) > 1) and (len(alias) > 1):
                names.append(name.lower())
                aliases.append(alias)
        username = self.settings.get('username', "")
        password = self.settings.get('password', "")
        servername = self.settings.get('servername', "")
        if (len(servername) == 0):
            LOGGER.info('Missing server name')
            return
        url = f'http://{servername}:9981/playlist/channels.m3u'
        r = requests.get(url, auth=(username, password))
        data = r.text.splitlines()
        if (r.status_code is not 200) or (len(r.text) < 100) or (data[0] != "#EXTM3U"):
            LOGGER.info('Unable to get channel list from server or wrong format')
            return
        i = 1
        ch_count = 0
        while i < len(data):
            try:
                i += 2
                extinf = data[i-2].split(',', 1)
                name = extinf[1]
                full_url = data[i-1].split('?', 1)
                url = f"http://{username}:{password}@{full_url[0][7:]}?profile=audio"
            except:
                LOGGER.info('Problem parsing channel info (wrong format?)')
                next
            if (len(name) < 2) or (len(url) < 50):
                LOGGER.info('Problem parsing channel info:\n' + data[i-2] + "\n" + data[i-1])
                next
            self.channels[name.lower()] = url
            ch_count += 1
            if name.lower() in names:
                alias = aliases[names.index(name.lower())]
                self.channels[alias.lower()] = url
                ch_count += 1
                LOGGER.info(f'Added alias "{alias}" for channel "{name}"')
        LOGGER.info(f"Added {ch_count} channels")


def create_skill():
    return TuneinRadio()
