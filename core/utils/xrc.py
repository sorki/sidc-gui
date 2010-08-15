# wx.xrc utils 

import os
import wx.xrc as xrc

xrc_cache = {}

def load(filepath):
    filepath = os.path.abspath(filepath)
    if reload or (filepath not in xrc_cache):
        result = xrc.XmlResource(filepath)
        xrc_cache[filepath] = result
    else:
        result = xrc_cache[filepath]

    return result

def get(id_or_name, scope=None):
    # prefer XRCCTRL, use XRCID if scope is None
    if scope is not None:
        res = xrc.XRCCTRL(scope, id_or_name)
    else:
        res = xrc.XRCID(id_or_name)

    return res




