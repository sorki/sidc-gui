import os
import wx
import psutil
import logging
import datetime
import threading

EVT_RESULT_ID = wx.NewId()

class ResultEvent(wx.PyEvent):
    ''' Event to carry arbitrary payload '''
    def __init__(self, data=(None,None)):
        super(ResultEvent, self).__init__()
        self.SetEventType(EVT_RESULT_ID)
        self.data = data

class WxThread(threading.Thread):
    ''' Generic wx worker thread '''
    def __init__(self, notify_window, on_result_fn, autostart=True):
        super(WxThread, self).__init__()
        self._notify_window = notify_window

        notify_window.Connect(-1, -1, EVT_RESULT_ID, on_result_fn)

        self._want_abort = 0

        if autostart:
            self.start()

    def run(self):
        raise NotImplemented

    def result(self, data):
        wx.PostEvent(self._notify_window, ResultEvent(data))

    def abort(self):
        self._want_abort = 1

        
class InfoThread(WxThread):
    def run(self):
        sidc_list = filter(lambda p: p.name == 'sidc', psutil.process_iter())

        if len(sidc_list)==0:
            logging.info('No sidc instance found. Live data disabled')
            self.result()
            return
        elif len(sidc_list)>1:
            logging.warning('Multiple sidc instances found - not supported')
            self.result()
            return

        sidc = sidc_list[0]

        sidc_status = {}
        attrs = '''
            pid path cmdline uid gid username create_time
            get_cpu_percent get_memory_percent
            '''

        for i in attrs.split():
            attrib = getattr(sidc, i)
            key = i.replace('get_', '')
            sidc_status[key] = attrib() if callable(attrib) else attrib

        sidc_status['create_datetime'] = datetime.datetime.fromtimestamp(
            sidc_status['create_time'])

        (sidc_status['cpu_user'],
            sidc_status['cpu_system']) = sidc.get_cpu_times()
        (sidc_status['mem_resident'],
            sidc_status['mem_virtual']) = sidc.get_memory_info()

        # find config

        # default location
        cfg_file = '/etc/sidc.conf'
        if os.path.exists(cfg_file):
            sidc_status['cfg_file'] = cfg_file
            logging.debug('Default sidc config file found')

        # custom location
        cmdline = ' '.join(sidc_status['cmdline'])
        find_result = cmdline.find('sidc ')
        if find_result != -1:
            params = cmdline[find_result+5:]
            pos = params.find('c ')
            if pos != -1:
                filename = params[pos+2:].split(' ')[0]
                cfg_file = os.path.join(sidc_status['path'], filename)
                if os.path.exists(cfg_file):
                    sidc_status['cfg_file'] = cfg_file
                    logging.debug('Custom sidc config file found')

        if 'cfg_file' not in sidc_status:
            logging.warning('Sidc is running but no config file found')
        else:
            if os.access(sidc_status['cfg_file'], os.R_OK):
                # config ok, read & parse
                cfg_contents = open(sidc_status['cfg_file']).readlines()
                cfg_contents = filter(lambda x: len(x)>0 and x[0] != ';',
                    map(lambda x: x.strip(), cfg_contents))

                bands = {}
                cfg = {}
                for item in cfg_contents:
                    parts = map(lambda x: x.strip(), item.split())
                    i = 1
                    while parts[i] != ';':
                        i += 1
                        if i == len(parts):
                            break

                    if parts[0] == 'band':
                        bands[parts[1]] = parts[2:i]
                    else:
                        # if options expects multiple args save them as list
                        cfg[parts[0]] = parts[1:i] if i>2 else parts[1]


                cfg['bands'] = bands
            else:
                logging.warning('Unable to read config file. Check permissions')

        self.result((sidc_status, cfg))
        return

