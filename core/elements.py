import wx
import logging

from utils import xrc
from utils.functional import paply
from threads import LoadThread

import matplotlib
matplotlib.use('WXAgg')
import matplotlib.cm as cm
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wx import NavigationToolbar2Wx


def build_tab(parent, filepath):
    res = xrc.load('xrc/load_panel.xrc')

    panel = res.LoadPanel(parent, 'Loaded')
    assert isinstance(panel, wx.Panel)

    panel.configure(parent, filepath)

    return panel

class LoadPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        pre = wx.PrePanel()
        # create step is handled by XRC
        self.PostCreate(pre)

   
    def configure(self, parent, filepath):
        self.parent = parent
        # Init panel controls

        # TODO (minor): maybe redundant if there's only cancel
        def bind_btn(btnid, fn):
            self.Bind(wx.EVT_BUTTON, fn, id=xrc.get(btnid))
        
        bind_btn('btn_load_cancel', self.on_cancel)

        # Start loading thread
        self.thread_load = LoadThread(self, self.on_load_result, False)

        fn = paply(self.thread_load.default_progress_fn, 
            wxgauge=xrc.get('progress_gauge', self))

        self.thread_load.configure(filepath, fn)
        self.thread_load.start()

    def on_cancel(self, event=None):
        self.thread_load.abort()
        self.parent.DeletePage(self.parent.GetSelection())

    def on_load_result(self, event=None): 
        logging.debug('Load result')
        if event.data is None:
            logging.debug('Load failure')
            # TODO (normal): handle failure
            pass
        else:
            # plot
            logging.debug('Data loaded, plotting')
            self.plot(event.data)
            self.thread_load = None

    def plot(self, data):
        xrc.get('load_progress', self).Hide()
        chart = xrc.get('chart_panel', self)
        self.plot = PlotPanel(chart)
        self.plot.init_plot()

        self.plot.plot(data, 'DCF')
        self.plot.plot(data, 'lrms')
        self.plot.plot(data, 'NRK')
        self.plot.plot(data, 'FTA')
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.plot, 1, wx.EXPAND)
        chart.SetSizer(sizer)

        self.Fit()


class PlotPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.fig = Figure((3.0,3.0), 100)
        #self.panel = wx.Panel(self)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.toolbar = NavigationToolbar2Wx(self.canvas) #matplotlib toolbar
        self.toolbar.Realize()
        #self.toolbar.set_active([0,1])

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)
        self.SetSizer(sizer)
        self.Fit()

    def init_plot(self):
        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('black')
        #self.axes.set_title('Sid data', size=12)

        '''
        self.plot_data = self.axes.plot(range(100), linewidth=1,
            color=(1,1,0))[0]

        self.plot_data2 = self.axes.plot(range(50), linewidth=1,
            color=(0,1,0))[0]
        '''
        self.toolbar.update()

    def plot(self, data, which):
        line = self.axes.plot(data['times'], data[which])
        setattr(self, which, line)

    def GetToolBar(self):
        return self.toolbar

    def onEraseBackground(self, evt):
        # this is supposed to prevent redraw flicker on some X servers...
        pass


