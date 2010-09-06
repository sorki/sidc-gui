import os
import io
import ConfigParser

# setup logging
#from logging import config as logging_cfg
#logging_cfg.fileConfig(os.path.join(os.path.dirname(__file__), 'logging.conf'))
# TODO (minor): logging configuration via ini config bellow
import logging
logging.basicConfig(level=logging.DEBUG)


defaults = '''
[config]
con_log_level = 20
last_data_path = %s
update_interval = 2

; valid color names - all html color names (http://www.w3schools.com/HTML/html_colornames.asp)
plot_color_cycle = blue green red cyan magenta yellow gray pink brown
plot_bg_color = black
plot_grid_color = gray
''' % os.path.expanduser('~')

class Config(object):
    def __init__(self):
        config = ConfigParser.RawConfigParser()
        self._filepath = os.path.join(os.path.expanduser('~'), '.sidcgui')
        config.readfp(io.BytesIO(defaults))
        config.read(self._filepath)

        self._config = config
        for item in config.options('config'):
            setattr(self, item, config.get('config', item).strip())
        return

    def save(self):
        config = self._config
        for item in config.options('config'):
            config.set('config', item, getattr(self, item))

        with open(self._filepath, 'wb') as cfgfile:
            config.write(cfgfile)
            cfgfile.close()

settings = Config()

