""" Emi
this application rapresent a multi link transmission. 
It will connect to x number of networks, Ethernets, Wifi, Satellite 
and transmit data to a selected one.  The selection can be manual or the
selection can based on networking performance
wifi      -> linked to router
ethernet  -> linked to a router or satellite
usb       -> linked to wifi or ethernet
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any, Tuple
import time
import asyncio
import logger as l
# --------------------------------------------
BUFFER = 65536
# --------------------------------------------
@dataclass
class Link:
    name:str
    bind_addr:Tuple[str,int]
    avg_rtt_ms:float = float('inf')
# --------------------------------------------
links = [
    Link( name='Link A(plusnet)', bind_addr=('192.168.1.109', 0)),
    Link( name='Link B(02-5G)', bind_addr=('192.168.68.51',0))
]
# --------------------------------------------
link_idx = 0
# --------------------------------------------
def select_link() -> Link:
    global link_idx
    link = links[link_idx % len(links)]
    link_idx += 1
    return link
# --------------------------------------------
async def close_writer(w):
    try:
        w.close(); await w.wait_closed()
    except:
        pass
# --------------------------------------------
async def pipe(r:asyncio.StreamReader, w:asyncio.StreamWriter, tag:str):
    addr = w.get_extra_info('peername')
    l.log(f'connected_client:{addr}:{tag}')
    try:
        while data := await r.read(BUFFER):
            w.write(data)
            await w.drain()
    except Exception as err:
        l.log(f'pipe_err:1000:{str(err)}', l.LogLevel.ERR)
    finally:
        await close_writer(w)
# -------------------------------------------
async def handle_client(
    client_r:asyncio.StreamReader,
    client_w:asyncio.StreamWriter,
    target_host:str,
    target_port:int,
    use_bind_addr: bool = True,
) -> None:
    selected_link = select_link()
    l.log(f'handle_client:selected={selected_link.name}')
    try:
        kwargs = {"host": target_host, "port": target_port}
        if use_bind_addr:
            kwargs["local_addr"] = selected_link.bind_addr
        upstream_r, upstream_w = await asyncio.open_connection(**kwargs)
        l.log(f'handle_client:connected_to_target')
        t1 = asyncio.create_task(pipe(client_r, upstream_w, 'C->>U'))
        t2 = asyncio.create_task(pipe(upstream_r, client_w, 'U->>C'))
        _, pending = await asyncio.wait(
            {t1, t2},
            return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
        for t in pending:
            try:
                await t
            except asyncio.CancelledError:
                pass
    except Exception as err:
        l.log(f'handle_client_err:1001:{str(err)}', l.LogLevel.ERR)
    finally:
        await close_writer(client_w)
# -------------------------------------------
async def main(target_host: str, target_port: int, local_port: int, use_bind_addr: bool = True):
    l.log('starting_server')
    def handler(r, w):
        return handle_client(r, w, target_host, target_port, use_bind_addr)
    server = await asyncio.start_server(handler, '0.0.0.0', local_port)
    l.log(f'server_started:{local_port=}:{target_host=}:{target_port}')
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('-H', '--host', default='34.13.59.163', help='target host')
    p.add_argument('-P', '--port', type=int, default=8010, help='target port')
    p.add_argument('-p', '--local-port', type=int, default=9010, help='listen port')
    p.add_argument('--no-bind', action='store_true', help='skip local_addr (for localhost testing)')
    args = p.parse_args()
    try:
        asyncio.run(main(args.host, args.port, args.local_port, use_bind_addr=not args.no_bind))
    except KeyboardInterrupt:
        l.log('exit')