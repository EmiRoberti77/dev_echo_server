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
from typing import Optional, Tuple, List
import asyncio
import logger as l
# --------------------------------------------
BUFFER = 65536
# --------------------------------------------
@dataclass
class Link:
    name:str
    bind_addr:Tuple[str,int]
    target_addr: Optional[Tuple[str, int]] = None
    avg_rtt_ms:float = float('inf')
# --------------------------------------------
links: List[Link] = [
    Link(name='Link A', bind_addr=('127.0.0.1', 0)),
    Link(name='Link B', bind_addr=('127.0.0.1', 0)),
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
    default_target_host:str,
    default_target_port:int,
    use_bind_addr: bool = True,
) -> None:
    selected_link = select_link()
    target_host, target_port = selected_link.target_addr or (default_target_host, default_target_port)
    l.log(
        f'handle_client:selected={selected_link.name}:'
        f'local={selected_link.bind_addr[0]}:'
        f'target={target_host}:{target_port}'
    )
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

    def parse_link_spec(spec: str) -> Link:
        # Format: NAME,BIND_IP,TARGET_IP[,TARGET_PORT]
        # Example: "wifi,192.168.68.50,192.168.68.51,8010"
        parts = [p.strip() for p in spec.split(",")]
        if len(parts) not in (3, 4):
            raise argparse.ArgumentTypeError(
                "Invalid --link format. Use NAME,BIND_IP,TARGET_IP[,TARGET_PORT]"
            )
        name, bind_ip, target_ip = parts[:3]
        target_port = int(parts[3]) if len(parts) == 4 else 0
        return Link(
            name=name,
            bind_addr=(bind_ip, 0),
            target_addr=(target_ip, target_port),
        )

    p = argparse.ArgumentParser()
    p.add_argument('-H', '--host', default='34.13.59.163', help='target host')
    p.add_argument('-P', '--port', type=int, default=8010, help='target port')
    p.add_argument('-p', '--local-port', type=int, default=9010, help='listen port')
    p.add_argument('--no-bind', action='store_true', help='skip local_addr (for localhost testing)')
    p.add_argument(
        '--link',
        action='append',
        default=[],
        metavar='NAME,BIND_IP,TARGET_IP[,TARGET_PORT]',
        help=(
            'repeat to define links; each link can override target per network '
            '(e.g. --link "eth0,192.168.2.188,192.168.1.109,8010" '
            '--link "wlan0,192.168.68.50,192.168.68.51,8010")'
        ),
    )
    args = p.parse_args()
    if args.link:
        parsed_links = [parse_link_spec(spec) for spec in args.link]
        for link in parsed_links:
            if link.target_addr is None:
                link.target_addr = (args.host, args.port)
            elif link.target_addr[1] == 0:
                link.target_addr = (link.target_addr[0], args.port)
        links = parsed_links
    else:
        links = [
            Link(name='Link A(eth0)', bind_addr=('192.168.2.188', 0), target_addr=(args.host, args.port)),
            Link(name='Link B(wlan0)', bind_addr=('192.168.68.50', 0), target_addr=(args.host, args.port)),
        ]
    l.log(f'configured_links={[(lk.name, lk.bind_addr, lk.target_addr) for lk in links]}')
    try:
        asyncio.run(main(args.host, args.port, args.local_port, use_bind_addr=not args.no_bind))
    except KeyboardInterrupt:
        l.log('exit')