import wx
import logging

class WxLogger(logging.Handler):
    def __init__(self, textarea=None):
        ''' 
        textarea - wxTextCtrl object (or any other
        object implementing AppendText(str) method 
        '''
        logging.Handler.__init__(self) # old style class :-S

        if textarea is None:
            raise TypeError('textarea of WxLogger is None')
        if not hasattr(textarea, 'AppendText'):
            raise AttributeError('object passed to WxLogger as textarea'+
                ' has no attribute \'AppendText\'')

        self.textarea = textarea

    def emit(self, record):
        # thread safe append
        wx.CallAfter(self.textarea.AppendText, self.format(record) + '\n')

