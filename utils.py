import logging

from PyQt5 import QtCore

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
fh = logging.StreamHandler()
fh_formatter = logging.Formatter(
    "%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
)
fh.setFormatter(fh_formatter)
logger.addHandler(fh)


class Worker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @QtCore.pyqtSlot()
    def run(self):
        self.fn(*self.args, **self.kwargs)
