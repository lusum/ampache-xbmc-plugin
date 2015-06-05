import xbmc
import os
import xbmcaddon
 
if __name__ == '__main__':
    ampache = xbmcaddon.Addon("plugin.audio.ampache")
    ampache_dir = xbmc.translatePath( ampache.getAddonInfo('path') )
    BASE_RESOURCE_PATH = os.path.join( ampache_dir, "resources" )
    mediaDir = os.path.join( BASE_RESOURCE_PATH , 'media' )
    cacheDir = os.path.join( mediaDir , 'cache' )
    
    extensions = ('.png', '.jpg')

    #clean cache on start
    for currentFile in os.listdir(cacheDir):
        print "processing file: " + str(currentFile)
        if any(currentFile.endswith(ext) for ext in extensions):
            pathDel = os.path.join( cacheDir, currentFile)
            os.remove(pathDel)
