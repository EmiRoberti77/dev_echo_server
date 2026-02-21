"""Diagnostic test for multi_link.
Usage:
  1. Run multi_link:  python multi_link.py -H localhost -P 8010
  2. Run echoserver: python echoserver.py -p 8010  (in echoserver folder)
  3. Run this test:  python test_multi_link.py
"""
import asyncio
import sys

async def test_connect(host='localhost', port=9000):
    print(f"Connecting to {host}:{port}...")
    try:
        reader, writer = await asyncio.open_connection(host, port)
        print("Connected!")
        msg = b"hello\n"
        writer.write(msg)
        await writer.drain()
        print(f"Sent: {msg!r}")
        data = await asyncio.wait_for(reader.read(4096), timeout=5.0)
        print(f"Received: {data!r} (len={len(data)})")
        writer.close()
        await writer.wait_closed()
        return True
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False

async def main():
    print("=== multi_link diagnostic ===\n")
    ok = await test_connect()
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    asyncio.run(main())
