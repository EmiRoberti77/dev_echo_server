import asyncio
import logger as l
import argparse
BUFFER = 4096
async def close_writer(w:asyncio.StreamWriter):
    try:
        w.close()
        await w.wait_closed()
    except:
        pass

async def handle_client(r:asyncio.StreamReader, w:asyncio.StreamWriter):
    l.log('handle client')
    addr = w.get_extra_info('peername')
    l.log(f'recieved connection from {addr}')

    while True:
        l.log('waiting to read')
        data = await r.read(BUFFER)
        l.log(f'read {len(data)}')
        if not data:
            l.log('no data recieved', l.LogLevel.WARN)
            break
        
        l.log(data)
        #send eco message
        try:
            l.log('sending response')
            w.write(data)
            await w.drain()
            l.log('sent response')
        except Exception as e:
            l.log('write exception', l.LogLevel.ERR)
            l.log(str(e))
            break
    
    await close_writer(w)
    l.log(f'disconneted from {addr}', l.LogLevel.ERR)


async def main(port:int=8010):
    server = await asyncio.start_server(handle_client,'0.0.0.0', port)
    l.log(f'server started {port=}')
    async with server:
        await server.serve_forever()
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', required=False)
    args = parser.parse_args()
    port = 8010
    if args.port is not None:
        port = int(args.port)
        l.log(f'set port to {port}')
    try:
        asyncio.run(main=main(port=port))
    except KeyboardInterrupt:
        pass