import xbmc
import os
import xbmcaddon
 
if __name__ == '__main__':
    ampache = xbmcaddon.Addon("plugin.audio.ampache")
    base_dir = xbmc.translatePath( ampache.getAddonInfo('profile')).decode('utf-8')
    mediaDir = os.path.join( base_dir , 'media' )
    cacheDir = os.path.join( mediaDir , 'cache' )
  
    #if cacheDir doesn't exist, create it
    if not os.path.isdir(mediaDir):
        os.mkdir(mediaDir)
        if not os.path.isdir(cacheDir):
            os.mkdir(cacheDir)
    extensions = ('.png', '.jpg')

    #clean cache on start
    for currentFile in os.listdir(cacheDir):
        #xbmc.log("Clear Cache Art " + str(currentFile),xbmc.LOGDEBUG)
        pathDel = os.path.join( cacheDir, currentFile)
        os.remove(pathDel)
