import asyncio
from dataclasses import asdict, dataclass
from enum import Enum
from datetime import datetime
import json

# Add at top - configure for YOUR machine's WiFi IPs
WIFI1_IP = '192.168.1.109'   # e.g. first WiFi interface IP
# WIFI2_IP = '172.20.10.2'     # e.g. second WiFi interface IP
WIFI2_IP = '192.168.0.100'

SERVER_HOST = ('34.13.59.163', 8010)

@dataclass
class Message:
    msg:str
    order:int
    link_name:str
    ts:str

class LogLevel(Enum):
    INFO = 'INFO'
    WARN = 'WARN'
    ERR = 'ERR'


def message(order:int, link_name:str)->str:
    m = Message(
        msg=f"order_{order}",
        order=order,
        link_name=link_name,
        ts=datetime.now().isoformat()
    )
    return json.dumps(asdict(m))


def logger(msg:str, level:LogLevel=LogLevel.INFO):
    ts = datetime.now().isoformat()
    print(f'[{ts}][{level.value}]=>{msg}')

async def close_writer(w:asyncio.StreamWriter):
    try:
        if not w.is_closing():
            w.close()
            await w.wait_closed()
    except:
        pass

async def start_message_broadact(r:asyncio.StreamReader, w:asyncio.StreamWriter, link_name:str)->None:
    logger(f'start_message_broadcast {link_name}')
    addr = w.get_extra_info('peername')
    logger(f'connected to {addr}')
    try:
        order = 0
        while True:
            msg = message(order, link_name)
            try:
                w.write(msg.encode('utf-8'))
                await w.drain()
                logger(f'data sent {link_name}')
            except (ConnectionError, TimeoutError, Exception) as e:
                logger(f'write error - {str(e)}', LogLevel.ERR)
            
            logger('waiting - read')
            data = await r.read(4096)
            logger(f'read {len(data)} bytes')
            if not data:
                logger(f'no data break {link_name}', LogLevel.ERR)
                break

            logger(data.decode('utf-8'))
            order += 1 
            await asyncio.sleep(2)
    except Exception as e:
        logger(f'gen error {link_name} {str(e)}', LogLevel.ERR)

    await close_writer(w)

async def main():
    logger('started')    
    reader_a, writer_a = await asyncio.open_connection(
       SERVER_HOST[0], SERVER_HOST[1], local_addr=(WIFI1_IP, 0)
    )

    reader_b, writer_b = await asyncio.open_connection(
        SERVER_HOST[0], SERVER_HOST[1], local_addr=(WIFI2_IP,0)
    )

    await asyncio.gather(
        start_message_broadact(reader_a, writer_a, 'link_a'),
        start_message_broadact(reader_b, writer_b, 'link_b')
    )

if __name__ == '__main__':
    try:
        asyncio.run(main=main())
    except KeyboardInterrupt:
        logger('exit')