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
        self.plot = PlotPanel(chart, data)
        self.plot.init_plot()

        #self.plot.plot('DCF')
        '''
        self.plot.plot(data, 'lrms')
        self.plot.plot(data, 'NRK')
        self.plot.plot(data, 'FTA')
        '''

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.plot, 1, wx.EXPAND)

        chart.SetSizer(sizer)

        self.Fit()


class PlotPanel(wx.Panel):
    def __init__(self, parent, data):
        wx.Panel.__init__(self, parent, -1)

        self.data = data
        self.fig = Figure((3.0,3.0), dpi=100)
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        '''
        http://matplotlib.sourceforge.net/users/event_handling.html

        def onmove(event):
            if event.inaxes:
                logging.debug('x=%d, y=%d, xdata=%f, ydata=%f' % (event.x, event.y,
                    event.xdata, event.ydata))

        self.canvas.mpl_connect('motion_notify_event', onmove)
        '''
        self.toolbar = NavigationToolbar2Wx(self.canvas) #matplotlib toolbar
        self.toolbar.Realize()
        #self.toolbar.set_active([0,1])
        self.init_controls()

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

#        self.axes.xaxis_date()
#        self.axes.set_xlabel('Datetime')
#        self.axes.set_xbound(lower=self.data['times'][0],
#            upper=self.data['times'][-1])


        #self.axes.set_title('Sid data', size=12)

        '''
        self.plot_data = self.axes.plot(range(100), linewidth=1,
            color=(1,1,0))[0]

        self.plot_data2 = self.axes.plot(range(50), linewidth=1,
            color=(0,1,0))[0]
        '''
        '''
        self.axes.xaxis.set_major_locator(dates.DayLocator())
        self.axes.xaxis.set_major_formatter(dates.DateFormatter('%d'))
        #ax.xaxis.set_minor_locator(months)
        self.axes.format_xdata = dates.DateFormatter('%d')
        '''
        def format_date(x, pos=None):
            logging.debug(x)
            return x.strftime('%Y-%d')

        #self.axes.xaxis.set_major_formatter(ticker.FuncFormatter(format_date))
        #lc = dates.AutoDateLocator()
        import matplotlib.dates as dates
        import matplotlib.ticker as ticker
        self.axes.xaxis.set_major_locator(ticker.LinearLocator())
        self.axes.xaxis.set_major_formatter(dates.DateFormatter('%H:%M:%S:%f'))
        self.axes.xaxis.set_minor_locator(ticker.LinearLocator())
        self.axes.format_xdata = dates.DateFormatter('%H:%M:%S')
        self.fig.autofmt_xdate()


        self.plot('DCF')
        #self.axes.set_autoscale_on(False)
        self.axes.set_xlim(lower=self.data['times'][0],
            upper=self.data['times'][-1])
        self.toolbar.update()

    def init_controls(self):
        self.controls = wx.Panel(self)
        csizer = wx.BoxSizer(wx.VERTICAL)
        dtypes = self.data.keys()
        dtypes.sort()
        for dtype in dtypes:
            if dtype != 'times':
                cbox = wx.CheckBox(self.controls, label=dtype)
                csizer.Add(cbox)
                self.Bind(wx.EVT_CHECKBOX, paply(self.on_band, dtype), cbox)
        btn = wx.Button(self.controls, -1, label='Re-scale')
        csizer.Add(btn)
        self.Bind(wx.EVT_BUTTON, self.on_scale, btn)
        self.controls.SetSizer(csizer)

    def on_scale(self, event=None):
        logging.debug('rescale')
        #self.axes.set_autoscale_on(True)
        #self.axes.autoscale_view()#scalex=False)
        ymin = min(self.data['DCF'])
        ymax = max(self.data['DCF'])
        self.axes.set_ybound(lower=ymin, upper=ymax)
        self.redraw()

    def on_band(self, which, event=None):
        if event is not None:
            obj = event.GetEventObject()
            if obj.IsChecked():
                self.plot(which)
            else:
                line = getattr(self, which)
                for index, _line in enumerate(self.axes.lines):
                    if _line == line:
                        break

                self.axes.lines.pop(index)
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


