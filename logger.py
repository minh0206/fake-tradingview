import logging

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)
fh = logging.StreamHandler()
fh_formatter = logging.Formatter(
    "%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
)
fh.setFormatter(fh_formatter)
logger.addHandler(fh)
