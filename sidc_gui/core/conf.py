import os
import io
import ConfigParser

defaults = '''
[config]
last_data_path = %s
''' % os.path.expanduser('~')

class Config(object):
    def __init__(self):
        config = ConfigParser.RawConfigParser()
        self._filepath = os.path.join(os.path.expanduser('~'), '.sidcgui')
        config.readfp(io.BytesIO(defaults))
        config.read(self._filepath)

        self._config = config
        for item in config.options('config'):
            setattr(self, item, config.get('config', item))
        return

    def save(self):
        config = self._config
        for item in config.options('config'):
            config.set('config', item, getattr(self, item))

        with open(self._filepath, 'wb') as cfgfile:
            config.write(cfgfile)
            cfgfile.close()

settings = Config()

