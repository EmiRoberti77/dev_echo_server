from enum import Enum
from datetime import datetime
import logger as l

class LogLevel(Enum):
    INFO = 'INFO'
    WARN = 'WARN'
    ERR = 'ERR'


def log(msg:str, level:LogLevel = LogLevel.INFO)->None:
    ts = datetime.now().isoformat()
    print(f'[{ts}]:[L:{level.value}]=>{msg}')