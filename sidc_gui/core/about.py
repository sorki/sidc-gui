import wx
import sidc_gui as package

def about_box(event):
    info = wx.AboutDialogInfo()

    info.SetName(package.__title__)
    info.SetVersion(package.__version__ + ' ' + package.__status__)
    info.SetDescription(package.__description__)
    info.SetCopyright(package.__copyright__)
    info.SetWebSite(package.__website__)
    info.SetLicence(package.__license__)
    info.AddDeveloper(package.__author__)
    info.AddDocWriter(package.__author__)

    wx.AboutBox(info)
