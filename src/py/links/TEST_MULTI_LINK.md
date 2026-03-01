# multi_link Test and Network Runbook

This file explains what was configured, how the two routes work, and how to test correctly.

## Current Design

`multi_link.py` listens locally (default `9010`) and forwards traffic to GCP (`34.13.59.163:8010`).

Two Pi source links are configured in code:

- Link A (Ethernet path): Pi `eth0` source bind
- Link B (WiFi path): Pi `wlan0` source bind

The code selects the best link by probe RTT (`select_best_link()`), not packet-level bonding.

## Final Addressing Used

### Raspberry Pi

- `eth0`: `192.168.137.2` (Windows ICS subnet)
- `wlan0`: `192.168.68.50`

### Windows Gateway

- `Ethernet`: `192.168.137.1` (set automatically by ICS)
- `WiFi 3`: `192.168.68.51` (internet uplink)

### Remote Target

- `34.13.59.163:8010`

## Network Diagram

```mermaid
flowchart LR
    PI[Raspberry Pi\neth0: 192.168.137.2\nwlan0: 192.168.68.50]
    WIN_ETH[Windows Ethernet\n192.168.137.1]
    WIN_WIFI[Windows WiFi 3\n192.168.68.51]
    ROUTER[Router\n192.168.68.1]
    GCP[GCP VM\n34.13.59.163:8010]

    PI -->|Path 1 (eth0 source)| WIN_ETH
    WIN_ETH --> WIN_WIFI
    WIN_WIFI --> ROUTER --> GCP

    PI -->|Path 2 (wlan0 source)| ROUTER
```

## Important Rules

1. `bind_addr` in Pi code must be Pi local IPs only.
   - Correct: `192.168.137.2`, `192.168.68.50`
   - Wrong: Windows IPs like `192.168.137.1` or `192.168.68.51`
2. If Windows ICS is enabled, Ethernet will usually be `192.168.137.1/24`.
3. If one path fails, traffic may only use the working path.

## Pi Routing Setup (Required)

Use source-based routing so each source IP exits the intended interface:

```bash
# Clear stale entries (safe if missing)
sudo ip rule del from 192.168.137.2/32 table 100 2>/dev/null || true
sudo ip rule del from 192.168.68.50/32 table 101 2>/dev/null || true
sudo ip route flush table 100
sudo ip route flush table 101

# Table 100: eth0 via Windows ICS
sudo ip route add 192.168.137.0/24 dev eth0 src 192.168.137.2 table 100
sudo ip route add default via 192.168.137.1 dev eth0 table 100
sudo ip rule add from 192.168.137.2/32 table 100 priority 100

# Table 101: wlan0 via local WiFi router
sudo ip route add 192.168.68.0/22 dev wlan0 src 192.168.68.50 table 101
sudo ip route add default via 192.168.68.1 dev wlan0 table 101
sudo ip rule add from 192.168.68.50/32 table 101 priority 101

sudo ip route flush cache
```

## Verification Checklist

### 1) L2/L3 reachability to Windows gateway (eth path)

```bash
ping -c 3 192.168.137.1
```

### 2) Route selection by source

```bash
ip route get 34.13.59.163 from 192.168.137.2
ip route get 34.13.59.163 from 192.168.68.50
```

Expected:

- `from 192.168.137.2` -> `via 192.168.137.1 dev eth0`
- `from 192.168.68.50` -> `via 192.168.68.1 dev wlan0`

### 3) TCP connectivity per source path

```bash
nc -s 192.168.137.2 -vz 34.13.59.163 8010
nc -s 192.168.68.50 -vz 34.13.59.163 8010
```

Both should succeed.

## Run multi_link

```bash
cd src/py/links
python3 multi_link.py -H 34.13.59.163 -P 8010 -p 9010
```

In another terminal, send test traffic to local proxy:

```bash
python3 test_multi_link.py
```

Or:

```bash
nc 127.0.0.1 9010
```

## Common Errors and Meaning

- `Errno 99 cannot assign requested address`
  - Bind IP is not local on Pi interface.
- `No route to host` on `nc -s ...`
  - Source path route/gateway/NAT is broken.
- `Destination Host Unreachable` ping to gateway
  - Local Ethernet adjacency issue (IP/subnet/cable/interface).

## What This Does Not Do Yet

This setup does not duplicate one TCP stream over both links simultaneously.
It chooses one link for each forwarded session based on current probe quality.
