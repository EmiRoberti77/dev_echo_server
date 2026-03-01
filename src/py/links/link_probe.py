""" Emi
This class is a asyncio task to probe a link and
gather average data for the link
"""
from collections import deque
from datetime import datetime
import asyncio
import time
from typing import Tuple
import logger as l

BUFFER = 65536

class Connection:
    def __init__(self, *, local_port:int=9010, target_host:str='34.13.59.163', target_port:int=8010,
                 link_host:str='', link_port:int=0, link_name:str=''):
        self.local_port = local_port
        self.target_host = target_host
        self.target_port = target_port
        self.link_host = link_host
        self.link_port = link_port
        self.link_name = link_name

def build_probe_payload(size_mb:int=4):
    return b'x' * (size_mb * 1024 * 1024)

class LinkProbe:
    def __init__(self, connection:Connection):
        self.connection = connection
        self.max_rtt_buf = 15
        self.rtt_ms_buffer = deque(maxlen=self.max_rtt_buf)

    @property
    def bind_addr(self):
        return (self.connection.link_host, self.connection.link_port)

    @property
    def name(self):
        return self.connection.link_name

    @property
    def avg_rtt_ms(self) -> float:
        if not self.rtt_ms_buffer:
            return float('inf')
        return sum(self.rtt_ms_buffer) / len(self.rtt_ms_buffer)
    
    async def close_writer(self, w):
        try:
            if not w.is_closing():
                w.close()
                await w.wait_closed()
        except:
            pass

    def record_rtt(self, rtt_ms: float):
        self.rtt_ms_buffer.append(rtt_ms)
        avg = sum(self.rtt_ms_buffer) / len(self.rtt_ms_buffer)
        l.log(f'{self.connection.link_name}:rtt_ms_buffer={len(self.rtt_ms_buffer)}:{avg=}')
        return avg
    
    async def probe_loop(self, interval: float = 10.0, payload_size_mb: float = 0.1):
        """Probe with fresh connection each cycle. Uses smaller payload to avoid server overload."""
        payload = b'x' * int(payload_size_mb * 1024 * 1024)  # 100KB default
        payload_size = len(payload)
        read_timeout = max(15, payload_size // 10000)  # ~15s min, scale with size
        l.log(f'probe_loop_start:{self.connection.link_name} payload={payload_size//1024}KB')
        while True:
            w = None
            try:
                kwargs = dict(host=self.connection.target_host, port=self.connection.target_port)
                if self.connection.link_host:
                    kwargs["local_addr"] = (self.connection.link_host, self.connection.link_port)
                r, w = await asyncio.open_connection(**kwargs)
                t_start = time.perf_counter()
                w.write(payload)
                await w.drain()
                received = await asyncio.wait_for(r.readexactly(payload_size), timeout=read_timeout)
                t_end = time.perf_counter()
                rtt_ms = (t_end - t_start) * 1000
                self.record_rtt(rtt_ms)
            except (asyncio.TimeoutError, ConnectionError, asyncio.IncompleteReadError) as err:
                l.log(f'probe_loop_error:{self.connection.link_name}:{str(err)}')
            except Exception as err:
                l.log(f'probe_loop_err:{str(err)}')
            finally:
                if w:
                    await self.close_writer(w)
            await asyncio.sleep(interval)

    async def start(self):
        probe_task = asyncio.create_task(self.probe_loop())
        l.log(f'start_task_create:{self.connection.link_name}')
        return probe_task
