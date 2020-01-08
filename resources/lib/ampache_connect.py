import hashlib
import ssl
import socket
import time, urllib,urllib2
import xbmc, xbmcaddon
import sys
import xml.etree.ElementTree as ET

from resources.lib import json_storage
from resources.lib import utils

class AmpacheConnect():
    
    class ConnectionError(Exception):
        pass
    
    def __init__(self):
        self._ampache = xbmcaddon.Addon("plugin.audio.ampache")
        jsStorServer = json_storage.JsonStorage("servers.json")
        serverStorage = jsStorServer.getData()
        self._connectionData = serverStorage["servers"][serverStorage["current_server"]]
        #self._connectionData = None
        self.filter=None
        self.add=None
        self.limit=5000
        self.offset=0
        self.type=None
        self.exact=None 
        self.mode=None
        self.id=None
  
    def get_user_pwd_login_url(self,nTime):
        myTimeStamp = str(nTime)
        enablePass = self._connectionData["enable_password"]
        if enablePass:
            sdf = self._connectionData["password"]
        else:
            sdf = ""
        hasher = hashlib.new('sha256')
        hasher.update(sdf)
        myKey = hasher.hexdigest()
        hasher = hashlib.new('sha256')
        hasher.update(myTimeStamp + myKey)
        myPassphrase = hasher.hexdigest()
        myURL = self._connectionData["url"] + '/server/xml.server.php?action=handshake&auth='
        myURL += myPassphrase + "&timestamp=" + myTimeStamp
        myURL += '&version=' + self._ampache.getSetting("api-version") + '&user=' + self._connectionData["username"]
        return myURL

    def get_auth_key_login_url(self):
        myURL = self._connectionData["url"] + '/server/xml.server.php?action=handshake&auth='
        myURL += self._connectionData["api_key"]
        myURL += '&version=' + self._ampache.getSetting("api-version")
        return myURL

    def handle_request(self,url):
        xbmc.log("AmpachePlugin::handle_request: url " + url, xbmc.LOGDEBUG)
        ssl_certs_str = self._ampache.getSetting("disable_ssl_certs")
        try:
            req = urllib2.Request(url)
            if utils.strBool_to_bool(ssl_certs_str):
                gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
                response = urllib2.urlopen(req, context=gcontext, timeout=400)
                xbmc.log("AmpachePlugin::handle_request: ssl",xbmc.LOGDEBUG)
            else:
                response = urllib2.urlopen(req, timeout=400)
                xbmc.log("AmpachePlugin::handle_request: nossl",xbmc.LOGDEBUG)
        except:
            xbmc.log("AmpachePlugin::handle_request ConnectionError",xbmc.LOGDEBUG)
            xbmc.executebuiltin("ConnectionError" )
            raise self.ConnectionError
        #headers = reponse.headers()
        #contents = reponse.read()
        return response

    def AMPACHECONNECT(self):
        jsStor = json_storage.JsonStorage("general.json")
        tempData = {}
        tempData["api-version"] = 350001
        tempData["artists"] = ""
        tempData["albums"] = ""
        tempData["songs"] = ""
        tempData["playlists"] = ""
        tempData["add"] = ""
        tempData["token"] = ""
        tempData["token-exp"] = ""
        socket.setdefaulttimeout(3600)
        nTime = int(time.time())
        use_api_key = self._connectionData["use_api_key"]
        if utils.strBool_to_bool(use_api_key):
            xbmc.log("AmpachePlugin::AMPACHECONNECT api_key",xbmc.LOGDEBUG)
            myURL = self.get_auth_key_login_url()
        else: 
            xbmc.log("AmpachePlugin::AMPACHECONNECT login password",xbmc.LOGDEBUG)
            myURL = self.get_user_pwd_login_url(nTime)
        try:
            response = self.handle_request(myURL)
        except self.ConnectionError:
            xbmc.log("AmpachePlugin::AMPACHECONNECT ConnectionError",xbmc.LOGDEBUG)
            raise self.ConnectionError
        xbmc.log("AmpachePlugin::AMPACHECONNECT ConnectionOk",xbmc.LOGDEBUG)
        contents = response.read()
        tree=ET.XML(contents)
        response.close()
        xbmc.log("AmpachePlugin::AMPACHECONNECT contents " + contents,xbmc.LOGDEBUG)
        errormess = tree.findtext('error')
        if errormess:
            errornode = tree.find("error")
            if errornode.attrib["code"]=="401":
                if "time" in errormess:
                    xbmc.executebuiltin("Notification(Error,If you are using Nextcloud don't check api_key box)")
                else:
                    xbmc.executebuiltin("Notification(Error,Connection error)")
            raise self.ConnectionError
            return
        token = tree.findtext('auth')
        version = tree.findtext('api')
        if not version:
        #old api
            version = tree.findtext('version')
        #setSettings only string or unicode
        tempData["api-version"] = version
        tempData["artists"] = tree.findtext("artists")
        tempData["albums"] = tree.findtext("albums")
        tempData["songs"] = tree.findtext("songs")
        tempData["playlists"] = tree.findtext("playlists")
        tempData["add"] = tree.findtext("add")
        tempData["token"] = token
        tempData["token-exp"] = str(nTime+24000)
        jsStor.save(tempData)
        return tree

    def ampache_http_request(self,action):
        thisURL = self.build_ampache_url(action)
        try:
            response = self.handle_request(thisURL)
        except self.ConnectionError:
            response.close()
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
        jsStor = json_storage.JsonStorage("general.json")
        tempData = jsStor.getData()
        tokenexp = int(tempData["token-exp"])
        if int(time.time()) > tokenexp:
            xbmc.log("refreshing token...", xbmc.LOGNOTICE )
            try:
                elem = self.AMPACHECONNECT()
            except:
                return

        token=tempData["token"]
        thisURL = self._connectionData["url"] + '/server/xml.server.php?action=' + action 
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

