import os
import wx
import logging
import commands
import datetime
import threading

EVT_RESULT_ID = wx.NewId()

class ResultEvent(wx.PyEvent):
    ''' Event to carry arbitrary payload '''
    def __init__(self, data):
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
        # keep args at the end as
        ps_format = 'comm,pid,user,time,%cpu,%mem,' \
            'policy,nice,etime,args'
        out = commands.getstatusoutput('ps ax -o %s | grep ^sidc' % ps_format)
        out_start = commands.getoutput('ps ax -o comm,lstart | grep ^sidc')
        

        sidc_status = {}

        if out[0] == 0:
            logging.debug('Found task matching \'sidc\'')
            sidc_status['start_time'] =  datetime.datetime.strptime(
                 out_start[4:].strip(), '%a %b  %d %H:%M:%S %Y')
            sproc = out[1].strip().split()

            ps_items = ps_format.split(',')
            for i, item in enumerate(ps_items):
                sidc_status[item] = (
                    sproc[i] if i+1 != len(ps_items) else ' '.join(sproc[i:]))


            out = commands.getstatusoutput(
                'cd /proc/%s/cwd; pwd -P' % sidc_status['pid'])
            fail = True
            if out[0] == 0:
                sidc_status['dir'] = out[1]

            # find config 
            
            # default location
            cfg_file = '/etc/sidc.conf'
            if os.path.exists(cfg_file):
                sidc_status['cfg_file'] = cfg_file
                logging.debug('Default sidc config file found')

            # custom location
            find_result = sidc_status['args'].find('sidc ')
            if find_result != -1:
                params = sidc_status['args'][find_result+5:]
                pos = params.find('c ') 
                if pos != -1:
                    filename = params[pos+2:].split(' ')[0]
                    cfg_file = os.path.join(sidc_status['dir'], filename)
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
                            sidc_status[parts[0]] = parts[1:i] if i>2 else parts[1]


                    sidc_status['bands'] = bands
                else:
                    logging.warning('Unable to read config file. Check permissions')

            self.result(sidc_status)
            return

        logging.info('No sidc instance found. Live data disabled')
        self.result(None)
