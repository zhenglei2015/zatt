import logging
import asyncio
from datetime import datetime
from .config import config


def tick():
    logger.debug('Tick: ' + datetime.now().isoformat('T'))
    loop = asyncio.get_event_loop()
    loop.call_later(1, tick)

if config['debug']:
    formatter_patten = '%(message)s'
    logLevel = logging.DEBUG
    loop = asyncio.get_event_loop()
    loop.call_later(1, tick)
else:
    logLevel = logging.INFO
    formatter_patten = '%(asctime)s %(message)s'

logger = logging.getLogger(__name__)
syslog = logging.StreamHandler()
formatter = logging.Formatter(formatter_patten)
syslog.setFormatter(formatter)
logger.setLevel(logLevel)
logger.addHandler(syslog)
