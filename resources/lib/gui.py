
import xbmc
import xbmcgui

def getFilterFromUser(title='',thisType=xbmcgui.INPUT_ALPHANUM):
    kb =  xbmcgui.Dialog()
    result = kb.input(title, type=thisType)
    if result:
        thisFilter = result
    else:
        return False
    return(thisFilter)

