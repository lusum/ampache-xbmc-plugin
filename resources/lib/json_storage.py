import json
import os
import xbmc
import xbmcaddon
import xbmcvfs
from copy import deepcopy

class JsonStorage():

    def __init__(self,filename):
        ampache = xbmcaddon.Addon("plugin.audio.ampache")
        ampache_dir = xbmc.translatePath( ampache.getAddonInfo('path') )
        self._BASE_RESOURCE_PATH = os.path.join( ampache_dir, 'resources' )
        self._filename = os.path.join(self._BASE_RESOURCE_PATH, filename)
        self._data = dict()
        self.load()

    def load(self):
        if xbmcvfs.exists(self._filename):
            with open(self._filename, 'r') as fd:
                self._data = json.load(fd)

    def save(self,data):
        if data != self._data:
            self._data = deepcopy(data)
            with open(self._filename, 'w') as fd:
                json.dump(self._data, fd, indent=4, sort_keys=True)

    def getData(self):
        return deepcopy(self._data)
