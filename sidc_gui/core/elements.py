import os
import wx
import logging
from datetime import timedelta

# matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wx import NavigationToolbar2Wx

import matplotlib.dates as dates
import matplotlib.ticker as ticker

# app core
from utils import xrc
from utils.functional import paply
from conf import settings
from threads import LoadThread, UpdateThread


def build_tab(parent, filepath):
    res = xrc.load('load_panel.xrc')

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

        def bind_btn(btnid, fn):
            self.Bind(wx.EVT_BUTTON, fn, id=xrc.get(btnid))
        
        bind_btn('btn_load_cancel', self.on_cancel)

        # Start loading thread
        self.thread_load = LoadThread(self, self.on_load_result, False)

        fn = paply(self.thread_load.default_progress_fn, 
            wxgauge=xrc.get('progress_gauge', self))

        self.thread_load.configure(filepath, fn)
        self.thread_load.start()

        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)

    def on_cancel(self, event=None):
        self.thread_load.abort()
        wx.CallAfter(self.parent.DeletePage, self.parent.GetSelection())

    def on_load_result(self, event=None): 
        logging.debug('Load result')
        if event.data is None:
            logging.debug('Load failure')
            dial = wx.MessageDialog(self, 'Error loading file, check console',
                'Error', wx.OK | wx.ICON_ERROR)
            dial.ShowModal()
            dial.Destroy()
            self.on_cancel()
        else:
            # plot
            logging.info('Data loaded, plotting')
            self.plot(event.data)

            self.thread_update = UpdateThread(self, self.on_update, False)
            self.thread_update.configure(self.filepath, 
                event.data['_last_red'], event.data['_last_mappings'],
                event.data['_bounds'], event.data['_time_bounds'])
            self.thread_update.start()

    def on_update(self, event=None):
        # event.data = data to be merged with current plot data
        self.plot.data['_bounds'] = event.data.pop('_bounds')
        self.plot.data['_time_bounds'] = event.data.pop('_time_bounds')
        self.plot.data['_times'] += event.data.pop('_times')

        for dtype,value in event.data.iteritems():
            self.plot.data[dtype] += value

            if hasattr(self.plot, dtype):
                line = getattr(self.plot, dtype)
                for index, _line in enumerate(self.plot.axes.lines):
                    if _line == line:
                        break

                self.plot.axes.lines[index].set_xdata(self.plot.data['_times'])
                self.plot.axes.lines[index].set_ydata(self.plot.data[dtype])

        live_mode = self.plot.controls.live_mode.GetSelection()
        xmax = self.plot.data['_times'][-1]
        if live_mode == 1:    #follow
            # TODO (normal): configurable live window size
            xmin = xmax - timedelta(minutes=10)
            self.plot.axes.set_xbound(lower=xmin, upper=xmax)
        elif live_mode == 2:  # scale x
            xmin = self.plot.data['_times'][0]
            self.plot.axes.set_xbound(lower=xmin, upper=xmax)

        self.plot.redraw()

    def on_destroy(self, event=None):
        '''
            End our threads gracefully
        '''
        if hasattr(self, 'thread_load') and self.thread_load is not None:
            self.thread_load.abort()
        if hasattr(self, 'thread_update') and self.thread_update is not None:
            self.thread_update.abort()

    def plot(self, data):
        xrc.get('load_progress', self).Hide()
        chart = xrc.get('chart_panel', self)
        if data['_times'] != []:
            title = data['_times'][int(len(data['_times'])/2)].strftime('%d %b %Y')
        else:
            title = os.path.basename(self.filepath)
        self.plot = PlotPanel(chart, data, title, self)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.plot, 1, wx.EXPAND)

        chart.SetSizer(sizer)

        self.Fit()


class PlotPanel(wx.Panel):
    def __init__(self, parent, data, title, page):
        wx.Panel.__init__(self, parent, -1)

        self.parent = page

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

        self.axes.set_title(self.title, size=12)
        self.axes.set_xlabel('Time [GMT]', labelpad=20)
        self.axes.set_ylabel('Signal strength [dB]', labelpad=20)

        clist = settings.plot_color_cycle.split(' ')
        self.axes.set_color_cycle(clist)
        self.axes.grid(True, color=settings.plot_grid_color)
        self.axes.set_axis_bgcolor(settings.plot_bg_color)

        def format_date(x, pos=None):
            dt = dates.num2date(x)
            main = dt.strftime('%H:%M:%S.')
            zeros_missing = 6-len(str(dt.microsecond))
            flo = float(".%s%d" % (zeros_missing*"0", dt.microsecond))
            return main + ('%.03f' % round(flo,3))[2:]

        self.axes.xaxis.set_major_locator(ticker.LinearLocator())
        self.axes.xaxis.set_major_formatter(ticker.FuncFormatter(format_date))
        self.axes.yaxis.set_major_locator(ticker.AutoLocator())
        # unused
        #self.axes.format_xdata = dates.DateFormatter('%H:%M:%S')
        self.fig.autofmt_xdate()

        self.plot(self.first_dtype)

        xmin = self.data['_times'][0]
        xmax = self.data['_times'][-1]
        self.axes.set_xbound(lower=xmin, upper=xmax)

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

        btn = wx.Button(self.controls, -1, label='Close file')
        add(btn)
        self.Bind(wx.EVT_BUTTON, self.parent.on_cancel, btn)

        label = wx.StaticText(self.controls, label='Bands:')
        add(label)

        for dtype in dtypes:
            if dtype[0] != '_':
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

        live_label = wx.StaticText(self.controls, label='Live mode:')
        choices = ['Update', 'Follow', 'Scale x']
        live_mode = wx.Choice(self.controls, -1, choices=choices)

        self.controls.live_mode = live_mode

        add(live_label)
        add(live_mode)

        self.controls.SetSizer(csizer)

    def rescale(self, event=None):
        ymin = 99999
        ymax = -ymin
        for dtype in self.data.keys():
            if hasattr(self, dtype):
                ymin = min(ymin, self.data['_bounds'][dtype][0])
                ymax = max(ymax, self.data['_bounds'][dtype][1])

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
        x = self.data['_times']
        y = self.data[which]
        t = self.data['_time_bounds'][which]

        if t != x[0]:
            logging.warning('Data type %s appeared later' % which)
            start = x.index(self.data['_time_bounds'][which])
            x = x[start:]

        if len(y) != len(x):
            x = x[:len(y)]

        line = self.axes.plot(x, y, scaley=False)[0]
#            marker='|', markerfacecolor='red')[0]

        setattr(self, which, line)
        self.redraw()

    def redraw(self):
        # update legend
        handles = []
        dtypes = []
        for dtype in self.data.keys():
            if hasattr(self, dtype):
                handles.append(getattr(self, dtype))
                dtypes.append(dtype)

        self.fig.legends = []
        if len(handles) != 0:
            self.fig.legend(handles, dtypes, 'right')

        # update tick style
        allticks = self.axes.xaxis.get_ticklines() + self.axes.yaxis.get_ticklines()
        for line in allticks:
            line.set_color('gray')
        # redraw
        self.canvas.draw()

    def GetToolBar(self):
        return self.toolbar

    def onEraseBackground(self, evt):
        # this is supposed to prevent redraw flicker on some X servers...
        pass


