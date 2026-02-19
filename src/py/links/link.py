"""
this application rapresents a link.  This is a transmission channel.
this is service is bidirectional sockets coms.
this could be a:
wifi      -> linked to router
ethernet  -> linked to a router or satellite
usb       -> linked to wifi or ethernet
"""
import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
import logger as l

SERVER_HOST = ('34.13.59.163', 8010)
BUFFER = 65536

def ts():
    return datetime.now().isoformat()

@dataclass
class Connection:
    local_port:int
    target_host:str
    target_port:int
    link_host:str
    link_port:int
    link_name:str

async def close_writer(w:asyncio.StreamWriter):
    try:
        if not w.is_closing():
            w.close()
            await w.wait_closed()
    except:
        pass

async def pipe(reader:asyncio.StreamReader, writer:asyncio.StreamWriter, tag:str):
    addr = writer.get_extra_info('peername')
    try:
        l.log(f'{tag}:connected {addr}')
        while True:
            data = await reader.read(BUFFER)
            if not data:
                l.log(f'{tag} data stopped', l.LogLevel.ERR)
                break
            try:
                writer.write(data)
                await writer.drain()
            except (asyncio.CancelledError, ConnectionError) as err:
                l.log(f'write error:1000:{str(err)}', l.LogLevel.ERR)
    except Exception as err:
        l.log(f'general error:1001:{str(err)}', l.LogLevel.ERR)
    finally:
        l.log('closing writer')
        await close_writer(writer)
        l.log('closed writer')

async def handle_client(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    upstream_host: str,
    upstream_port: int,
    bind_addr: Optional[Tuple[str, int]] = None
) -> None:
    upstream_reader: Optional[asyncio.StreamReader] = None
    upstream_writer: Optional[asyncio.StreamWriter] = None
    try:
        kwargs = {"host": upstream_host, "port": upstream_port}
        if bind_addr:
            kwargs["local_addr"] = bind_addr
        upstream_reader, upstream_writer = await asyncio.open_connection(**kwargs)
        t1 = asyncio.create_task(pipe(client_reader, upstream_writer, 'c>>u'))
        t2 = asyncio.create_task(pipe(upstream_reader, client_writer, 'u>>c'))
        _ , pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
    except Exception as e:
        l.log(f'handle client err:1002:{str(e)}', l.LogLevel.ERR)
    finally:
        l.log('handle_client:closing writer')
        await close_writer(client_writer)
        l.log('handle_client:closed writer')

async def main(connection: Connection):
    l.log(connection)
    uhost, uport = connection.target_host, connection.target_port
    bind_addr = (connection.link_host, connection.link_port) if connection.link_host else None
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, uhost, uport, bind_addr),
        host='0.0.0.0',
        port=connection.local_port,
        reuse_address=True
    )
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='link service')
    parser.add_argument('-H', '--host', type=str, required=True, help='target upstream host')
    parser.add_argument('-P', '--port', default=8010, type=int, help='target upstream port')
    parser.add_argument('-p', '--local-port', default=8010, type=int, help='local listen port')
    parser.add_argument('-B', '--bind', type=str, default='',
                        help='local interface IP to bind outgoing connections (e.g. 192.168.1.109 for WiFi)')
    parser.add_argument('-N', '--name', type=str, required=True)
    parser.add_argument('-L', '--link', type=str, required=True)
    args = parser.parse_args()
    connection = Connection(
        local_port=args.local_port,
        target_host=args.host,
        target_port=args.port,
        link_host=args.bind,
        link_port=0,
        link_name=args.name
    )
    asyncio.run(main(connection))
