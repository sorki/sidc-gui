import os
import wx
import logging

from utils import xrc
from utils.functional import paply
from threads import LoadThread

from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wx import NavigationToolbar2Wx

import matplotlib.dates as dates
import matplotlib.ticker as ticker


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
        self.filepath = filepath
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
        # TODO (major): parse date from filename according to config or guess format
        title = os.path.basename(self.filepath)
        self.plot = PlotPanel(chart, data, title)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.plot, 1, wx.EXPAND)

        chart.SetSizer(sizer)

        self.Fit()


class PlotPanel(wx.Panel):
    def __init__(self, parent, data, title):
        wx.Panel.__init__(self, parent, -1)

        self.data = data
        self.title = title
        self.fig = Figure((3.0,3.0), dpi=100)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        # TODO (minor): exact value according to mouse position 
        '''
        http://matplotlib.sourceforge.net/users/event_handling.html

        def onmove(event):
            if event.inaxes:
                logging.debug('x=%d, y=%d, xdata=%f, ydata=%f' % (event.x, event.y,
                    event.xdata, event.ydata))

        self.canvas.mpl_connect('motion_notify_event', onmove)
        '''
        self.toolbar = NavigationToolbar2Wx(self.canvas)
        self.toolbar.Realize()
        self.init_controls()
        self.init_plot()

        self.lcol = wx.BoxSizer(wx.VERTICAL)
        self.lcol.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.lcol.Add(self.toolbar, 0, wx.GROW)
        self.rcol = wx.BoxSizer(wx.VERTICAL)
        self.rcol.Add(self.controls, 0, wx.EXPAND)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.lcol, 1, wx.EXPAND)
        self.sizer.Add(self.rcol, 0)

        self.SetSizer(self.sizer)
        self.Fit()

    def init_plot(self):
        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('black')
        self.axes.grid(True, color='gray')

        self.axes.set_title(self.title, size=12)
        self.axes.set_xlabel('Time')
        self.axes.set_ylabel('Value')


        def format_date(x, pos=None):
            dt = dates.num2date(x)
            main = dt.strftime('%H:%M:%S.')#dates.DateFormatter('%H:%M:%S:%f'))
            zeros_missing = 6-len(str(dt.microsecond))
            flo = float(".%s%d" % (zeros_missing*"0", dt.microsecond))
            return main + ('%.03f' % round(flo,3))[2:]

        self.axes.xaxis.set_major_locator(ticker.LinearLocator())
        self.axes.xaxis.set_major_formatter(ticker.FuncFormatter(format_date))
        self.axes.xaxis.set_minor_locator(ticker.LinearLocator())
        # unused
        #self.axes.format_xdata = dates.DateFormatter('%H:%M:%S')
        self.fig.autofmt_xdate()


        self.plot(self.first_dtype)

        self.axes.set_autoscale_on(False)
        self.autoscale = False

        self.rescale()
        self.toolbar.update()

    def init_controls(self):
        self.controls = wx.Panel(self)
        csizer = wx.BoxSizer(wx.VERTICAL)
        dtypes = self.data.keys()
        dtypes.sort()
        fst = True
        add = paply(csizer.Add, border=5, flag=wx.ALL)
        add_cb = paply(csizer.Add, border=5, flag=wx.LEFT|wx.RIGHT)

        label = wx.StaticText(self.controls, label='Bands:')
        add(label)

        for dtype in dtypes:
            if dtype != 'times' and dtype != 'bounds':
                cbox = wx.CheckBox(self.controls, label=dtype)
                if fst:
                    fst = False
                    self.first_dtype = dtype
                    cbox.SetValue(True)
                add_cb(cbox)
                self.Bind(wx.EVT_CHECKBOX, paply(self.on_band, dtype), cbox)
        btn = wx.Button(self.controls, -1, label='Re-scale')
        add(btn)
        self.Bind(wx.EVT_BUTTON, self.rescale, btn)

        auto = wx.CheckBox(self.controls, label='Autoscale')
        add_cb(auto)
        self.Bind(wx.EVT_CHECKBOX, self.on_autoscale, auto)
        self.controls.SetSizer(csizer)

    def rescale(self, event=None):
        ymin = 99999
        ymax = -ymin
        for dtype in self.data.keys():
            if hasattr(self, dtype):
                ymin = min(ymin, self.data['bounds'][dtype][0])
                ymax = max(ymax, self.data['bounds'][dtype][1])

        # 1% spacing
        corr = (ymax - ymin)/100
        self.axes.set_ybound(lower=ymin-corr, upper=ymax+corr)
        self.redraw()

    def on_autoscale(self, event=None):
        if event is not None:
            obj = event.GetEventObject()
            self.autoscale = obj.IsChecked()

    def on_band(self, which, event=None):
        if event is not None:
            obj = event.GetEventObject()
            if obj.IsChecked():
                self.plot(which)
                if self.autoscale:
                    self.rescale()
            else:
                line = getattr(self, which)
                for index, _line in enumerate(self.axes.lines):
                    if _line == line:
                        break

                self.axes.lines.pop(index)
                delattr(self, which)
                if self.autoscale:
                    self.rescale()
                self.redraw()


    def plot(self, which):
        line = self.axes.plot(self.data['times'], self.data[which])[0]
        setattr(self, which, line)
        self.redraw()

    def redraw(self):
        self.canvas.draw()

    def GetToolBar(self):
        return self.toolbar

    def onEraseBackground(self, evt):
        # this is supposed to prevent redraw flicker on some X servers...
        pass


