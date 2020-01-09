import sys
import os
import re
import random,xbmcplugin,xbmcgui,urllib
import datetime
import xml.etree.ElementTree as ET
import xbmcaddon

from resources.lib import ampache_connect
from resources.lib import json_storage
from resources.lib import servers_manager
from resources.lib import gui

# Shared resources

ampache = xbmcaddon.Addon("plugin.audio.ampache")

ampache_addon_path =  ampache.getAddonInfo('path').decode('utf-8')
ampache_dir = xbmc.translatePath( ampache_addon_path )
BASE_RESOURCE_PATH = os.path.join( ampache_dir, 'resources' )
mediaDir = os.path.join( BASE_RESOURCE_PATH , 'media' )
user_dir = xbmc.translatePath( ampache.getAddonInfo('profile')).decode('utf-8')
user_mediaDir = os.path.join( user_dir , 'media' )
cacheDir = os.path.join( user_mediaDir , 'cache' )
imagepath = os.path.join( mediaDir ,'images')

def cacheArt(url):
        ampacheConnect = ampache_connect.AmpacheConnect()
	strippedAuth = url.split('&')
	imageID = re.search(r"id=(\d+)", strippedAuth[0])
        #security check:
        #also nexcloud server doesn't send images
        if imageID == None:
            raise NameError
        
        imageNamePng = imageID.group(1) + ".png"
        imageNameJpg = imageID.group(1) + ".jpg"
        pathPng = os.path.join( cacheDir , imageNamePng )
        pathJpg = os.path.join( cacheDir , imageNameJpg )
	if os.path.exists( pathPng ):
                xbmc.log("AmpachePlugin::CacheArt: png cached",xbmc.LOGDEBUG)
		return pathPng
        elif os.path.exists( pathJpg ):
                xbmc.log("AmpachePlugin::CacheArt: jpg cached",xbmc.LOGDEBUG)
		return pathJpg
	else:
                xbmc.log("AmpachePlugin::CacheArt: File needs fetching ",xbmc.LOGDEBUG)
                headers,contents = ampacheConnect.handle_request(url)
		if headers.maintype == 'image':
			extension = headers['content-type']
			tmpExt = extension.split("/")
			if tmpExt[1] == "jpeg":
				fname = imageNameJpg
			else:
				fname = imageID.group(1) + '.' + tmpExt[1]
                        pathJpg = os.path.join( cacheDir , fname )
			open( pathJpg, 'wb').write(contents)
                        xbmc.log("AmpachePlugin::CacheArt: Cached " + str(fname), xbmc.LOGDEBUG )
			return pathJpg
		else:
                        xbmc.log("AmpachePlugin::CacheArt: It didnt work", xbmc.LOGDEBUG )
                        raise NameError
			#return False

#return album and artist name, only album could be confusing
def get_album_artist_name(node):
    fullname = node.findtext("name").encode("utf-8")
    fullname += " - "
    fullname += node.findtext("artist").encode("utf-8")
    return fullname

def get_artLabels(albumArt):
    art_labels = {
            'banner' : albumArt, 
            'thumb': albumArt, 
            'icon': albumArt,
            'fanart': albumArt
            }
    return art_labels

def get_art(node):
    try:
        albumArt = cacheArt(node.findtext("art"))
    except NameError:
        albumArt = "DefaultFolder.png"
    xbmc.log("AmpachePlugin::get_art: albumArt - " + str(albumArt), xbmc.LOGDEBUG )
    return albumArt

def get_infolabels(object_type , node):
    infoLabels = None
    if object_type == 'albums':
        infoLabels = {
            'Title' : unicode(node.findtext("name")) ,
            'Album' : unicode(node.findtext("name")) ,
            'Artist' : unicode(node.findtext("artist")),
            'Discnumber' : unicode(node.findtext("disk")),
            'Year' : node.findtext("year") ,
            'Rating' : node.findtext("preciserating"),
            'Mediatype' : 'album'
        }
 
    elif object_type == 'artists':
        
        infoLabels = {
            'Title' : unicode(node.findtext("name")) ,
            'Artist' : unicode(node.findtext("name")),
            'Rating' : node.findtext("preciserating"),
            'Mediatype' : 'artist'
        }

    elif object_type == 'songs':
        infoLabels = {
            'Title' : unicode(node.findtext("title")) ,
            'Artist' : unicode(node.findtext("artist")),
            'Album' :  unicode(node.findtext("album")),
            'Size' : node.findtext("size") ,
            'Duration' : node.findtext("time"),
            'Year' : node.findtext("year") ,
            'Tracknumber' : node.findtext("track"),
            'Rating' : node.findtext("preciserating"),
            'Mediatype' : 'song'
        }

    return infoLabels

#handle albumArt and song info
def fillListItemWithSongInfo(liz,node):
    albumArt = get_art(node)
    liz.setLabel(unicode(node.findtext("title")))
    liz.setArt( get_artLabels(albumArt) )
    #needed by play_track to play the song, added here to uniform api
    liz.setPath(node.findtext("url"))
    liz.setInfo( type="music", infoLabels=get_infolabels("songs", node) )
    liz.setMimeType(node.findtext("mime"))

# Used to populate items for songs on XBMC. Calls plugin script with mode == 9 and object_id == (ampache song id)
# TODO: Merge with addDir(). Same basic idea going on, this one adds links all at once, that one does it one at a time
#       Also, some property things, some different context menu things.
def addSongLinks(elem):
   
    #win_id is necessary to avoid problems in musicplaylist window, where this
    #script doesn't work
    curr_win_id = xbmcgui.getCurrentWindowId()
    xbmcplugin.setContent(int(sys.argv[1]), "songs")
    ok=True
    it=[]
    for node in elem.iter("song"):
        liz=xbmcgui.ListItem()
        fillListItemWithSongInfo(liz,node)
        liz.setProperty("IsPlayable", "true")

        cm = []
        try:
            artist_elem = node.find("artist")
            artist_id = int(artist_elem.attrib["id"])
            cm.append( ( "Show artist from this song",
            "Container.Update(%s?object_id=%s&mode=15&win_id=%s)" % (
                sys.argv[0],artist_id, curr_win_id ) ) )
        except:
            pass
        
        try:
            album_elem = node.find("album")
            album_id = int(album_elem.attrib["id"])
            cm.append( ( "Show album from this song",
            "Container.Update(%s?object_id=%s&mode=16&win_id=%s)" % (
                sys.argv[0],album_id, curr_win_id ) ) )
        except:
            pass
        
        try:
            song_elem = node.find("song")
            song_title = unicode(node.findtext("title"))
            cm.append( ( "Search all songs with this title",
            "Container.Update(%s?title=%s&mode=17&win_id=%s)" % (
                sys.argv[0],song_title, curr_win_id ) ) )
        except:
            pass

        if cm != []:
            liz.addContextMenuItems(cm)

        #song_elem = node.find("song")
        #song_id = int(node.attrib["id"])
        song_url = node.findtext("url")
        track_parameters = { "mode": 9, "song_url" : song_url}
        url = sys.argv[0] + '?' + urllib.urlencode(track_parameters)
        tu= (url,liz)
        it.append(tu)
    
    ok=xbmcplugin.addDirectoryItems(handle=int(sys.argv[1]),items=it,totalItems=len(elem))
    xbmc.log("AmpachePlugin::addSongLinks " + str(ok), xbmc.LOGDEBUG)
    return ok

# The function that actually plays an Ampache URL by using setResolvedUrl. Gotta have the extra step in order to make
# song album art / play next automatically. We already have the track URL when we add the directory item so the api
# hit here is really unnecessary. Would be nice to get rid of it, the extra request adds to song gaps. It does
# guarantee that we are using a legit URL, though, if the session expired between the item being added and the actual
# playing of that item.
def play_track(song_url):
    #''' Start to stream the track with the given id. '''
    #ampConn = ampache_connect.AmpacheConnect()

    #try:
    #    ampConn.filter = id 
    #    elem = ampConn.ampache_http_request("song")
    #except:
    #    return
    #for thisnode in elem:
    #    node = thisnode
    liz = xbmcgui.ListItem()
    #fillListItemWithSongInfo(liz,node)
    liz.setPath(song_url)
    xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True,listitem=liz)

# Main function for adding xbmc plugin elements
def addDir(name,object_id,mode,iconImage=None,elem=None,infoLabels=None):
    if iconImage == None:
        iconImage = "DefaultFolder.png"
    
    if infoLabels == None:
        infoLabels={ "Title": name }
    
    liz=xbmcgui.ListItem(name)
    liz.setInfo( type="Music", infoLabels=infoLabels )
    liz.setArt(  get_artLabels(iconImage) )
    liz.setProperty('IsPlayable', 'false')

    try:
        artist_elem = elem.find("artist")
        artist_id = int(artist_elem.attrib["id"]) 
        cm = []
        cm.append( ( "Show all albums from artist", "Container.Update(%s?object_id=%s&mode=2)" % ( sys.argv[0],artist_id ) ) )
        liz.addContextMenuItems(cm)
    except:
        pass

    u=sys.argv[0]+"?object_id="+str(object_id)+"&mode="+str(mode)+"&name="+urllib.quote_plus(name)
    xbmc.log("AmpachePlugin::addDir name " + name + " url " + u, xbmc.LOGDEBUG)
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=True)
    #xbmc.log("AmpachePlugin::addDir ok " + str(ok), xbmc.LOGDEBUG)
    return ok

#catch all function to add items to the directory using the low level addDir
#or addSongLinks functions
def addItem( object_type, mode , elem, useCacheArt=True):
    image = "DefaultFolder.png"
    xbmc.log("AmpachePlugin::addItem: object_type - " + str(object_type) , xbmc.LOGDEBUG )
    if object_type == 'albums':
        allid = set()
        for node in elem.iter('album'):
            #no unicode function, cause urllib quot_plus error ( bug )
            album_id = int(node.attrib["id"])
            #remove duplicates in album names ( workaround for a problem in server comunication )
            if album_id not in allid:
                allid.add(album_id)
            else:
                continue
            fullname = get_album_artist_name(node)
            if useCacheArt:
                image = get_art(node)
            addDir(fullname,node.attrib["id"],mode,image,node,infoLabels=get_infolabels("albums",node))
    elif object_type == 'artists':
        for node in elem.iter('artist'):
            addDir(node.findtext("name").encode("utf-8"),node.attrib["id"],mode,image,node,infoLabels=get_infolabels("artists",node))
    elif object_type == 'playlists':
        for node in elem.iter('playlist'):
            addDir(node.findtext("name").encode("utf-8"),node.attrib["id"],mode,image,node)
    elif object_type == 'tags':
        for node in elem.iter('tag'):
            addDir(node.findtext("name").encode("utf-8"),node.attrib["id"],mode,image,node)
    elif object_type == 'songs':
        addSongLinks(elem)

def get_time(time_offset):
    d = datetime.date.today()
    dt = datetime.timedelta(days=time_offset)
    nd = d + dt
    return nd.isoformat()

def get_items(object_type, object_id=None, add=None,
        thisFilter=None,limit=5000,useCacheArt=True, object_subtype=None, exact=None ):
    
    if object_type:
        xbmc.log("AmpachePlugin::get_items: object_type " + object_type, xbmc.LOGDEBUG)
    else:
        #should be not possible
        xbmc.log("AmpachePlugin::get_items: object_type set to None" , xbmc.LOGDEBUG)
        return
    
    if object_subtype:
        xbmc.log("AmpachePlugin::get_items: object_subtype " + object_subtype, xbmc.LOGDEBUG)
    if object_id:
        xbmc.log("AmpachePlugin::get_items: object_id " + str(object_id), xbmc.LOGDEBUG)

    jsStor = json_storage.JsonStorage("general.json")
    tempData = jsStor.getData()

    if limit == None:
        limit = int(tempData[object_type])
    mode = None

    xbmcplugin.setContent(int(sys.argv[1]), object_type)
    #default: object_type is the action,otherwise see the if list below
    action = object_type
    
    #do not use action = object_subtype cause in tags it is used only to
    #discriminate between subtypes
    if object_type == 'albums':
        if object_subtype == 'artist_albums':
            action = 'artist_albums'
            addDir("All Songs",object_id,12)
        elif object_subtype == 'tag_albums':
            action = 'tag_albums'
        elif object_subtype == 'album':
            action = 'album'
    elif object_type == 'artists':
        if object_subtype == 'tag_artists':
            action = 'tag_artists'
        if object_subtype == 'artist':
            action = 'artist'
    elif object_type == 'songs':
        if object_subtype == 'tag_songs':
            action = 'tag_songs'
        elif object_subtype == 'playlist_songs':
            action = 'playlist_songs'
        elif object_subtype == 'album_songs':
            action = 'album_songs'
        elif object_subtype == 'artist_songs':
            action = 'artist_songs'
        elif object_subtype == 'search_songs':
            action = 'search_songs'

    if object_id:
        thisFilter = object_id
    
    try:
        ampConn = ampache_connect.AmpacheConnect()
        ampConn.add = add
        ampConn.filter = thisFilter
        ampConn.limit = limit
        ampConn.exact = exact

        elem = ampConn.ampache_http_request(action)
    except:
        return

    #after the request, set the mode 

    if object_type == 'artists':
        mode = 2
    elif object_type == 'albums':
        mode = 3
    elif object_type == 'playlists':
        mode = 14
    if object_type == 'tags':
        if object_subtype == 'tag_artists':
            mode = 19
        elif object_subtype == 'tag_albums':
            mode = 20
        elif object_subtype == 'tag_songs':
            mode = 21

    addItem( object_type, mode , elem, useCacheArt)

def do_search(object_type,object_subtype=None,thisFilter=None):
    if not thisFilter:
        thisFilter = gui.getFilterFromUser()
    if thisFilter:
        get_items(object_type=object_type,thisFilter=thisFilter,object_subtype=object_subtype)
        return True
    return False

def get_stats(object_type, object_subtype=None, limit=5000 ):       
    
    ampConn = ampache_connect.AmpacheConnect()
    jsStor = json_storage.JsonStorage("general.json")
    tempData = jsStor.getData()
    
    xbmc.log("AmpachePlugin::get_stats ",  xbmc.LOGDEBUG)
    mode = None
    if object_type == 'artists':
        mode = 2
    elif object_type == 'albums':
        mode = 3
   
    xbmcplugin.setContent(int(sys.argv[1]), object_type)

    action = 'stats'
    if(tempData["api-version"]) < 400001:
        amtype = object_subtype
        thisFilter = None
    else:
        if object_type == 'albums':
            amtype='album'
        elif object_type == 'artists':
            amtype='artist'
        elif object_type == 'songs':
            amtype='song'
        thisFilter = object_subtype
    
    try:
        ampConn.filter = thisFilter
        ampConn.limit = limit
        ampConn.type = amtype
                
        elem = ampConn.ampache_http_request(action)
    except:
        return
  
    addItem( object_type, mode , elem)

def get_recent(object_type,object_id,object_subtype=None):   
    jsStor = json_storage.JsonStorage("general.json")
    tempData = jsStor.getData()

    if object_id == 9999998:
        update = tempData["add"]        
        xbmc.log(update[:10],xbmc.LOGNOTICE)
        get_items(object_type=object_type,add=update[:10],object_subtype=object_subtype)
    elif object_id == 9999997:
        get_items(object_type=object_type,add=get_time(-7),object_subtype=object_subtype)
    elif object_id == 9999996:
        get_items(object_type=object_type,add=get_time(-30),object_subtype=object_subtype)
    elif object_id == 9999995:
        get_items(object_type=object_type,add=get_time(-90),object_subtype=object_subtype)

def get_random(object_type):
    xbmc.log("AmpachePlugin::get_random: object_type " + object_type, xbmc.LOGDEBUG)
    mode = None
    #object type can be : albums, artists, songs, playlists
    
    ampConn = ampache_connect.AmpacheConnect()
    jsStor = json_storage.JsonStorage("general.json")
    tempData = jsStor.getData()
    
    if object_type == 'albums':
        amtype='album'
        mode = 3
    elif object_type == 'artists':
        amtype='artist'
        mode = 2
    elif object_type == 'playlists':
        amtype='playlist'
        mode = 14
    elif object_type == 'songs':
        amtype='song'
    
    xbmcplugin.setContent(int(sys.argv[1]), object_type)
        
    random_items = (int(ampache.getSetting("random_items"))*3)+3
    xbmc.log("AmpachePlugin::get_random: random_items " + str(random_items), xbmc.LOGDEBUG )
    items = int(tempData[object_type])
    xbmc.log("AmpachePlugin::get_random: total items in the catalog " + str(items), xbmc.LOGDEBUG )
    if random_items > items:
        #if items are less than random_itmes, return all items
        get_items(object_type, limit=items)
        return
    #playlists are not in the new stats api, so, use the old mode
    if(int(tempData["api-version"])) >= 400001 and object_type != 'playlists':
        action = 'stats'
        thisFilter = 'random'
        try:
            ampConn.filter = thisFilter
            ampConn.limit = random_items
            ampConn.type = amtype

            elem = ampConn.ampache_http_request(action)
            addItem( object_type, mode , elem)
        except:
            return
    
    else: 
        seq = random.sample(xrange(items),random_items)
        xbmc.log("AmpachePlugin::get_random: seq " + str(seq), xbmc.LOGDEBUG )
        elements = []
        for item_id in seq:
            try:
                ampConn.offset = item_id
                ampConn.limit = 1
                elem = ampConn.ampache_http_request(object_type)
                elements.append(elem)
            except:
                pass
   
        for el in elements:
            addItem( object_type, mode , el)
        
def get_params():
    xbmc.log("AmpachePlugin::get_params 0 " + sys.argv[0], xbmc.LOGDEBUG)
    xbmc.log("AmpachePlugin::get_params 1 " + sys.argv[1], xbmc.LOGDEBUG)
    xbmc.log("AmpachePlugin::get_params 2 " + sys.argv[2], xbmc.LOGDEBUG)
    param=[]
    paramstring=sys.argv[2]
    if len(paramstring)>=2:
            params=sys.argv[2]
            cleanedparams=params.replace('?','')
            if (params[len(params)-1]=='/'):
                    params=params[0:len(params)-2]
            pairsofparams=cleanedparams.split('&')
            param={}
            for i in range(len(pairsofparams)):
                    splitparams={}
                    splitparams=pairsofparams[i].split('=')
                    if (len(splitparams))==2:
                            param[splitparams[0]]=splitparams[1]
                            
    return param

if (__name__ == '__main__'):
    params=get_params()
    name=None
    mode=None
    object_id=None
    win_id=None
    title=None
    song_url=None
    
    try:
            name=urllib.unquote_plus(params["name"])
            xbmc.log("AmpachePlugin::name " + name, xbmc.LOGDEBUG)
    except:
            pass
    try:
            mode=int(params["mode"])
            xbmc.log("AmpachePlugin::mode " + str(mode), xbmc.LOGDEBUG)
    except:
            pass
    try:
            object_id=int(params["object_id"])
            xbmc.log("AmpachePlugin::object_id " + str(object_id), xbmc.LOGDEBUG)
    except:
            pass
    try:
            win_id=int(params["win_id"])
            xbmc.log("AmpachePlugin::win_id " + str(win_id), xbmc.LOGDEBUG)
    except:
            pass
    try:
            title=urllib.unquote_plus(params["title"])
            xbmc.log("AmpachePlugin::title " + title, xbmc.LOGDEBUG)
    except:
            pass
    try:
            song_url=urllib.unquote_plus(params["song_url"])
            xbmc.log("AmpachePlugin::song_url " + song_url, xbmc.LOGDEBUG)
    except:
            pass


    jsStor = json_storage.JsonStorage("general.json")
    tempData = jsStor.getData()
    
    servers_manager.initialiseServer()
    
    ampacheConnect = ampache_connect.AmpacheConnect()

    if mode==None:
        try:
            elem = ampacheConnect.AMPACHECONNECT()
        except:
            elem = ET.Element("")
        
        addDir("Search...",None,4,"DefaultFolder.png")
        addDir("Quick access...",None,25,"DefaultFolder.png")
        addDir("Explore...",None,23,"DefaultFolder.png")
        addDir("Library...",None,24,"DefaultFolder.png")
        addDir("Switch server",None,44,"DefaultFolder.png")
        addDir("Settings",None,40,"DefaultFolder.png")
        
    #   artist list ( called from main screen  ( mode None ) , search
    #   screen ( mode 4 ) and recent ( mode 5 )  )

    elif mode==1:
        #artist, album, songs, playlist follow the same structure
        #search function
        num_items = (int(ampache.getSetting("random_items"))*3)+3
        #recent function
        if object_id > 9999994 and object_id < 9999999:
            get_recent( "artists", object_id )
        elif object_id == 9999994:
            #removed cause nasty recursive call using some commands in web interface
            #addDir("Refresh..",9999994,2,os.path.join(imagepath,'refresh_icon.png'))
            get_random('artists')
        elif object_id == 9999993:
            get_stats(object_type="artists",object_subtype="hightest",limit=num_items)
        elif object_id == 9999992:
            get_stats(object_type="artists",object_subtype="frequent",limit=num_items)
        elif object_id == 9999991:
            get_stats(object_type="artists",object_subtype="flagged",limit=num_items)
        elif object_id == 9999990:
            get_stats(object_type="artists",object_subtype="forgotten",limit=num_items)
        elif object_id == 9999989:
            get_stats(object_type="artists",object_subtype="newest",limit=num_items)
        #get all artists
        else:
            get_items("artists", limit=None, useCacheArt=False)
           
    #   albums list ( called from main screen ( mode None ) , search
    #   screen ( mode 4 ) and recent ( mode 5 )  )

    elif mode==2:
        num_items = (int(ampache.getSetting("random_items"))*3)+3
        if object_id > 9999994 and object_id < 9999999:
            get_recent( "albums", object_id )
        elif object_id == 9999994:
            #removed cause nasty recursive call using some commands in web interface
            #addDir("Refresh..",9999990,2,os.path.join(imagepath, 'refresh_icon.png'))
            get_random('albums')
        elif object_id == 9999993:
            get_stats(object_type="albums",object_subtype="hightest",limit=num_items)
        elif object_id == 9999992:
            get_stats(object_type="albums",object_subtype="frequent",limit=num_items)
        elif object_id == 9999991:
            get_stats(object_type="albums",object_subtype="flagged",limit=num_items)
        elif object_id == 9999990:
            get_stats(object_type="albums",object_subtype="forgotten",limit=num_items)
        elif object_id == 9999989:
            get_stats(object_type="albums",object_subtype="newest",limit=num_items)
        elif object_id:
            get_items(object_type="albums",object_id=object_id,object_subtype="artist_albums")
        #get all albums
        else:
            get_items("albums", limit=None, useCacheArt=False)

    #   song mode ( called from search screen ( mode 4 ) and recent ( mode 5 )  )
            
    elif mode==3:
        num_items = (int(ampache.getSetting("random_items"))*3)+3
        if object_id > 9999994 and object_id < 9999999:
            get_recent( "songs", object_id )
        elif object_id == 9999994:
            #removed cause nasty recursive call using some commands in web interface
            #addDir("Refresh..",9999994,2,os.path.join(imagepath, 'refresh_icon.png'))
            get_random('songs')
        elif object_id == 9999993:
            get_stats(object_type="songs",object_subtype="hightest",limit=num_items)
        elif object_id == 9999992:
            get_stats(object_type="songs",object_subtype="frequent",limit=num_items)
        elif object_id == 9999991:
            get_stats(object_type="songs",object_subtype="flagged",limit=num_items)
        elif object_id == 9999990:
            get_stats(object_type="songs",object_subtype="forgotten",limit=num_items)
        elif object_id == 9999989:
            get_stats(object_type="songs",object_subtype="newest",limit=num_items)
        else:
            get_items(object_type="songs",object_id=object_id,object_subtype="album_songs")


    # search screen ( called from main screen )

    elif mode==4:      
        dialog = xbmcgui.Dialog()
        ret = dialog.contextmenu(['Artist', 'Album', 'Song','Playlist','All','Tag'])
        endDir = False
        if ret == 0:
            endDir = do_search("artists")
        elif ret == 1:
            endDir = do_search("albums")
        elif ret == 2:
            endDir = do_search("songs")
        elif ret == 3:
            endDir = do_search("playlists")
        elif ret == 4:
            endDir = do_search("songs","search_songs")
        elif ret == 5:
            ret2 = dialog.contextmenu(['Artist tag', 'Album tag', 'Song tag'])        
            if ret2 == 0:
                endDir = do_search("tags","tag_artists")
            elif ret2 == 1:
                endDir = do_search("tags","tag_albums")
            elif ret2 == 2:
                endDir = do_search("tags","tag_songs")

        if endDir == False:
            #no end directory item
            mode = 100 

    # recent additions screen ( called from main screen )

    elif mode==5:
        addDir("Recent Artists...",9999998,6,"DefaultFolder.png")
        addDir("Recent Albums...",9999997,6,"DefaultFolder.png")
        addDir("Recent Songs...",9999996,6,"DefaultFolder.png")
        addDir("Recent Playlists...",9999995,6,"DefaultFolder.png")

    #   screen with recent time possibilities ( subscreen of recent artists,
    #   recent albums, recent songs ) ( called from mode 5 )

    elif mode==6:
        #not clean, but i don't want to change too much the old code
        if object_id > 9999995:
            #object_id for playlists is 9999995 so 9999999-object_id is 4 that is search mode
            #i have to use another method, so i use the hardcoded mode number (13)
            mode_new = 9999999-object_id
        elif object_id == 9999995:
            mode_new = 13
        
        addDir("Last Update",9999998,mode_new,"DefaultFolder.png")
        addDir("1 Week",9999997,mode_new,"DefaultFolder.png")
        addDir("1 Month",9999996,mode_new,"DefaultFolder.png")
        addDir("3 Months",9999995,mode_new,"DefaultFolder.png")

    # general random mode screen ( called from main screen )

    elif mode==7:
        addDir("Random Artists...",9999994,1,"DefaultFolder.png")
        addDir("Random Albums...",9999994,2,"DefaultFolder.png")
        addDir("Random Songs...",9999994,3,"DefaultFolder.png")
        addDir("Random Playlists...",9999994,13,"DefaultFolder.png")

    #old mode 
    #
    #random mode screen ( display artists, albums or songs ) ( called from mode
    #   7  )
    #elif mode==8:
    #end old mode

    #   play track mode  ( mode set in add_links function )

    elif mode==9:
        play_track(song_url)

    # mode 12 : artist_songs
    elif mode==12:
        get_items(object_type="songs",object_id=object_id,object_subtype="artist_songs" )

    #   playlist full list ( called from main screen )

    elif mode==13:
            if object_id > 9999994 and object_id < 9999999:
                get_recent( "playlists", object_id )
            elif object_id == 9999994:
                #removed cause nasty recursive call using some commands in web interface
                #addDir("Refresh..",9999994,2,os.path.join(imagepath, 'refresh_icon.png'))
                get_random('playlists')
            elif object_id:
                get_items(object_type="playlists",object_id=object_id)
            else:
                get_items(object_type="playlists")

    #   playlist song mode

    elif mode==14:
        get_items(object_type="songs",object_id=object_id,object_subtype="playlist_songs")

    elif mode==15:
        if xbmc.getCondVisibility("Window.IsActive(musicplaylist)"):
            xbmc.executebuiltin("ActivateWindow(%s)" % (win_id,))
        get_items(object_type="artists",object_id=object_id,object_subtype="artist")

    elif mode==16:
        if xbmc.getCondVisibility("Window.IsActive(musicplaylist)"):
            xbmc.executebuiltin("ActivateWindow(%s)" % (win_id,))
        get_items(object_type="albums",object_id=object_id,object_subtype="album")

    elif mode==17:
        if xbmc.getCondVisibility("Window.IsActive(musicplaylist)"):
            xbmc.executebuiltin("ActivateWindow(%s)" % (win_id,))
        endDir = do_search("songs",thisFilter=title)
        if endDir == False:
            #no end directory item
            mode = 100 

    elif mode==18:
        addDir("Artist tags...",object_id,19)
        addDir("Album tags...",object_id,20)
        addDir("Song tags...",object_id,21)

    elif mode==19:
        if object_id:
            get_items(object_type="artists", object_subtype="tag_artists",object_id=object_id)
        else:
            get_items(object_type = "tags", object_subtype="tag_artists")

    elif mode==20:
        if object_id:
            get_items(object_type="albums", object_subtype="tag_albums",object_id=object_id)
        else:
            get_items(object_type = "tags", object_subtype="tag_albums")

    elif mode==21:
        if object_id:
            get_items(object_type="songs", object_subtype="tag_songs",object_id=object_id)
        else:
            get_items(object_type = "tags", object_subtype="tag_songs")

    elif mode==23:
        addDir("Recent...",None,5,"DefaultFolder.png")
        addDir("Random...",None,7,"DefaultFolder.png")
        if(int(tempData["api-version"])) >= 400001:
            addDir("Hightest Rated...",9999993,30)
            addDir("Frequent...",9999992,31)
            addDir("Flagged...",9999991,32)
            addDir("Forgotten...",9999990,33)
            addDir("Newest...",9999989,34)

    elif mode==24:
        addDir("Artists (" + tempData["artists"]+ ")",None,1,"DefaultFolder.png")
        addDir("Albums (" + tempData["albums"] + ")",None,2,"DefaultFolder.png")
        addDir("Playlists (" + tempData["playlists"] + ")",None,13,"DefaultFolder.png")
        addDir("Tags",None,18,"DefaultFolder.png")
    
    elif mode==25:
        addDir("Recent Albums...",9999997,6,"DefaultFolder.png")
        addDir("Random Albums...",9999994,2,"DefaultFolder.png")
        if(int(tempData["api-version"])) >= 400001:
            addDir("Newest Albums...",9999989,2)
            addDir("Frequent Albums...",9999992,2)
        addDir("Server playlist...",9999994,3,"DefaultFolder.png")

    elif mode==30:
        addDir("Hightest Rated Artists...",9999993,1)
        addDir("Hightest Rated Albums...",9999993,2)
        addDir("Hightest Rated Songs...",9999993,3)

    elif mode==31:
        addDir("Frequent Artists...",9999992,1)
        addDir("Frequent Albums...",9999992,2)
        addDir("Frequent Songs...",9999992,3)

    elif mode==32:
        addDir("Flagged Albums...",9999991,2)
        addDir("Flagged Songs...",9999991,3)
        addDir("Flagged Artists...",9999991,1)

    elif mode==33:
        addDir("Forgotten Artists...",9999990,1)
        addDir("Forgotten Albums...",9999990,2)
        addDir("Forgotten Songs...",9999990,3)
    
    elif mode==34:
        addDir("Newest Artists...",9999989,1)
        addDir("Newest Albums...",9999989,2)
        addDir("Newest Songs...",9999989,3)
    
    elif mode==40:
        ampache.openSettings()

    elif mode==41:
        if servers_manager.addServer():
            servers_manager.switchServer()
    
    elif mode==42:
        if servers_manager.deleteServer():
            servers_manager.switchServer()
    
    elif mode==43:
        servers_manager.modifyServer()
    
    elif mode==44:
        servers_manager.switchServer()
            
    if mode < 40:
        xbmc.log("AmpachePlugin::endOfDirectory " + sys.argv[1],  xbmc.LOGDEBUG)
        xbmcplugin.endOfDirectory(int(sys.argv[1]))
