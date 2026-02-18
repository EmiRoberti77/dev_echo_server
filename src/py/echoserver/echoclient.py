import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import logger as l
UTF8 = 'utf-8'

@dataclass
class Message:
    ts:str
    msg:str
    order:int

def get_message(order:int):
    msg = Message(
        ts=datetime.now().isoformat(),
        msg='echo',
        order=order
    )
    msg = json.dumps(asdict(msg))
    l.log(msg)
    return msg

async def handle_tcp_connection(r:asyncio.StreamReader, w:asyncio.StreamWriter):
    count = 0
    while True:
        try:
            try:
                w.write(get_message(order=count).encode(UTF8))
                await w.drain()
            except Exception as e:
                l.log('write error', l.LogLevel.ERR)
                l.log(str(e), l.LogLevel.ERR)
            
            count += 1
            l.log('waiting to read')
            data = await r.read(4096)
            l.log(f'data read {len(data)}')
            if not data:
                l.log('no data break', l.LogLevel.ERR)
                break

            l.log('sleep')
            await asyncio.sleep(2)
        
            l.log('closing writer')
        except ConnectionError:
            l.log('Connection error or disconnect', l.LogLevel.ERR)
        except Exception as e:
            l.log(str(e))

    try:
        w.close()
        await w.wait_closed()
    except Exception as e:
        l.log('closing writer err', l.LogLevel.ERR)
        l.log(str(e))
    
    l.log('closed writer')

async def main(host:str = 'localhost', port:int = 8010):
    reader, writer = await asyncio.open_connection(host, port)
    addr = writer.get_extra_info('peername')
    l.log(f'connected {addr}')
    await handle_tcp_connection(reader, writer)

if __name__ == '__main__':
    try:
        asyncio.run(main=main())
    except KeyboardInterrupt:
        pass
    