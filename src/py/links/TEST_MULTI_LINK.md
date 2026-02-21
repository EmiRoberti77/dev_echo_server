# multi_link Testing Guide

## Summary

multi_link **is working**. The diagnostic test connects, sends data, and receives a response. Fixes applied:

1. **handle_client**: Added `finally` to close `client_w`, await cancelled tasks
2. **pipe**: Removed dead `w.wait_closed` line
3. **CLI**: Added `-H`, `-P`, `-p`, `--no-bind` for flexible testing

## How to Test

### Option A: With remote target (34.13.59.163)
```bash
# Terminal 1: Start multi_link (default target)
cd src/py/links
python multi_link.py

# Terminal 2: Connect client to multi_link on port 9000
python echoclient.py -H localhost -P 9000
```

**Important**: Client must use port **9000** (multi_link), not 8010 (target).

### Option B: With local echo server (full local test)
```bash
# Terminal 1: Start echo server
cd src/py/echoserver
python echoserver.py -p 8010

# Terminal 2: Start multi_link (target localhost)
cd src/py/links
python multi_link.py -H localhost -P 8010 --no-bind

# Terminal 3: Run test
python test_multi_link.py
```

Use `--no-bind` when testing with localhost because `local_addr` (192.168.x.x) is for external interfaces.

### Option C: Target remote with specific bind
```bash
python multi_link.py -H 34.13.59.163 -P 8010
# Uses Link A or B (192.168.1.109 / 192.168.68.51) for outgoing connections
```

## Troubleshooting

| Symptom | Cause |
|---------|-------|
| No data received | Client connecting to wrong port (8010 instead of 9000) |
| handle_client_err | Target unreachable or wrong host/port; try `--no-bind` for localhost |
| "command not recognised" | Target at 34.13.59.163 is not a simple echo server |
