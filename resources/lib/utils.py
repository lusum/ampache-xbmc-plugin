import time
import xbmcaddon

ampache = xbmcaddon.Addon("plugin.audio.ampache")

def int_to_strBool(s):
    if s == 1:
        return 'true'
    elif s == 0:
        return 'false'
    else:
        raise ValueError

#   string to bool function : from string 'true' or 'false' to boolean True or
#   False, raise ValueError
def strBool_to_bool(s):
    if s == 'true':
        return True
    elif s == 'false':
        return False
    else:
        raise ValueError

def check_tokenexp():
    tokenexp = int(ampache.getSetting("token-exp"))
    if int(time.time()) > tokenexp:
        return True
    return False
