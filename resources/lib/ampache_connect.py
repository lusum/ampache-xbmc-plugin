import hashlib
import ssl
import socket
import time, urllib,urllib2
import xbmc
import xbmcaddon
import sys
import xml.etree.ElementTree as ET

from resources.lib import json_storage

class AmpacheConnect():
    
    class ConnectionError(Exception):
        pass
    
    def __init__(self):
        self._ampache = xbmcaddon.Addon("plugin.audio.ampache")
        self.filter=None
        self.add=None
        self.limit=5000
        self.offset=0
        self.type=None
        self.exact=None 
        self.mode=None
        self.id=None
    
    #   string to bool function : from string 'true' or 'false' to boolean True or
    #   False, raise ValueError
    def str_to_bool(self,s):
        if s == 'true':
            return True
        elif s == 'false':
            return False
        else:
            raise ValueError
   
    def get_user_pwd_login_url(self,nTime):
        myTimeStamp = str(nTime)
        sdf = self._ampache.getSetting("password")
        hasher = hashlib.new('sha256')
        hasher.update(self._ampache.getSetting("password"))
        myKey = hasher.hexdigest()
        hasher = hashlib.new('sha256')
        hasher.update(myTimeStamp + myKey)
        myPassphrase = hasher.hexdigest()
        myURL = self._ampache.getSetting("server") + '/server/xml.server.php?action=handshake&auth='
        myURL += myPassphrase + "&timestamp=" + myTimeStamp
        myURL += '&version=' + self._ampache.getSetting("api-version") + '&user=' + self._ampache.getSetting("username")
        return myURL

    def get_auth_key_login_url(self):
        myURL = self._ampache.getSetting("server") + '/server/xml.server.php?action=handshake&auth='
        myURL += self._ampache.getSetting("api_key")
        myURL += '&version=' + self._ampache.getSetting("api-version")
        return myURL

    def handle_request(self,url):
        try:
            xbmc.log(url,xbmc.LOGNOTICE)
            req = urllib2.Request(url)
            ssl_certs_str = self._ampache.getSetting("disable_ssl_certs")
            if self.str_to_bool(ssl_certs_str):
                gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
                response = urllib2.urlopen(req, context=gcontext, timeout=400)
                xbmc.log("AmpachePlugin::AmpacheConnect: ssl",xbmc.LOGDEBUG)
            else:
                response = urllib2.urlopen(req, timeout=400)
                xbmc.log("AmpachePlugin::AmpacheConnect: nossl",xbmc.LOGDEBUG)
        except:
            xbmc.log("AmpachePlugin::ConnectionError",xbmc.LOGDEBUG)
            xbmc.executebuiltin("ConnectionError" )
            raise self.ConnectionError
        return response

    def AMPACHECONNECT(self):
        jsStor = json_storage.JsonStorage("general.json")
        tempData = {}
        socket.setdefaulttimeout(3600)
        nTime = int(time.time())
        use_api_key = self._ampache.getSetting("use_api_key")
        if self.str_to_bool(use_api_key):
            myURL = self.get_auth_key_login_url() 
        else: 
            myURL = self.get_user_pwd_login_url(nTime)
        try:
            response = self.handle_request(myURL)
        except self.ConnectionError:
            raise self.ConnectionError
        tree=ET.parse(response)
        response.close()
        elem = tree.getroot()
        token = elem.findtext('auth')
        version = elem.findtext('api')
        if not version:
        #old api
            version = elem.findtext('version')
        #setSettings only string or unicode
        tempData["api-version"] = version
        tempData["artists"] = elem.findtext("artists")
        tempData["albums"] = elem.findtext("albums")
        tempData["songs"] = elem.findtext("songs")
        tempData["playlists"] = elem.findtext("playlists")
        tempData["add"] = elem.findtext("add")
        jsStor.save(tempData)
        self._ampache.setSetting('token',token)
        self._ampache.setSetting('token-exp',str(nTime+24000))
        return elem

    def ampache_http_request(self,action):
        thisURL = self.build_ampache_url(action)
        try:
            response = self.handle_request(thisURL)
        except self.ConnectionError:
            raise self.ConnectionError
        contents = response.read()
        contents = contents.replace("\0", "")
        #remove bug & it is not allowed as text in tags
        
        #code useful for debugging/parser needed
        xbmc.log("AmpachePlugin::ampache_http_request: contents " + contents, xbmc.LOGDEBUG)
        #parser = ET.XMLParser(recover=True)
        #tree=ET.XML(contents, parser = parser)
        tree=ET.XML(contents)
        response.close()
        if tree.findtext("error"):
            errornode = tree.find("error")
            if errornode.attrib["code"]=="401":
                try:
                    tree = self.AMPACHECONNECT()
                except self.ConnectionError:
                    raise self.ConnectionError
                thisURL = self.build_ampache_url(action)
                try:
                    response = self.handle_request(thisURL)
                except self.ConnectionError:
                    raise self.ConnectionError
                contents = response.read()
                tree=ET.XML(contents)
                response.close()
        return tree
    
    def build_ampache_url(self,action):
        tokenexp = int(self._ampache.getSetting('token-exp'))
        if int(time.time()) > tokenexp:
            xbmc.log("refreshing token...", xbmc.LOGNOTICE )
            try:
                elem = self.AMPACHECONNECT()
            except:
                return

        token=self._ampache.getSetting('token')    
        thisURL = self._ampache.getSetting("server") + '/server/xml.server.php?action=' + action 
        thisURL += '&auth=' + token
        thisURL += '&limit=' +str(self.limit)
        thisURL += '&offset=' +str(self.offset)
        if self.filter:
            thisURL += '&filter=' +urllib.quote_plus(str(self.filter))
        if self.add:
            thisURL += '&add=' + self.add
        if self.type:
            thisURL += '&type=' + self.type
        if self.mode:
            thisURL += '&mode=' + self.mode
        if self.exact:
            thisURL += '&exact=' + self.exact
        if self.id:
            thisURL += '&id=' + self.id
        return thisURL





