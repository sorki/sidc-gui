# wx.xrc utils 

import os
import wx.xrc as xrc
import logging

xrc_cache = {}

def load(filepath):
    logging.debug('Loading xrc - %s' % filepath)
    filepath = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', '..', 'xrc', filepath))

    if reload or (filepath not in xrc_cache):
        logging.debug('Fetching xrc from file')
        if os.path.isfile(filepath):
            result = xrc.XmlResource(filepath)
            xrc_cache[filepath] = result
        else:
            logging.error('Xrc file missing')
            return None
    else:
        logging.debug('Fetching xrc from cache')
        result = xrc_cache[filepath]

    logging.debug('Xrc loaded')
    return result

def get(id_or_name, scope=None):
    # prefer XRCCTRL, use XRCID if scope is None
    if scope is not None:
        res = xrc.XRCCTRL(scope, id_or_name)
    else:
        res = xrc.XRCID(id_or_name)

    return res




