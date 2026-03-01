# Network Integration Report

## Goal

Configure the Raspberry Pi app (`src/py/links/multi_link.py`) to use two network paths toward the same remote service (`34.13.59.163:8010`), with Windows providing gateway/NAT on the Ethernet path.

---

## Final Topology

```text
Path A (Direct WiFi route):

Raspberry Pi wlan0: 192.168.68.50/22
        |
        v
Router: 192.168.68.1
        |
        v
GCP VM: 34.13.59.163:8010


Path B (Ethernet -> Windows gateway route):

Raspberry Pi eth0: 192.168.137.2/24
        |
        v
Windows Ethernet: 192.168.137.1/24 (ICS internal side)
        |
        v
Windows WiFi 3: 192.168.68.51/22 (internet uplink)
        |
        v
Router: 192.168.68.1
        |
        v
GCP VM: 34.13.59.163:8010
```

---

## What We Observed During Debugging

1. `multi_link.py` started and accepted links, but one path failed.
2. Attempts to bind to Windows IPs from Pi caused local bind errors:
   - `[Errno 99] cannot assign requested address`
3. `nc -s 192.168.2.188 -vz 34.13.59.163 8010` failed while WiFi path succeeded.
4. ARP and ping to Windows Ethernet failed when Pi was on `192.168.2.x`.
5. After enabling ICS on Windows, Windows Ethernet changed to `192.168.137.1`.
6. Pi Ethernet needed to move to the same ICS subnet (`192.168.137.x`).

---

## Root Causes

- Incorrect source bind IP used in app on Pi (Windows IP was used at least once).
- Route policy initially sent both sources out `wlan0`.
- Windows ICS/NAT changed Ethernet subnet to `192.168.137.1/24`, but Pi still used `192.168.2.x`.

---

## Final Address Plan

### Windows

- `WiFi 3`: `192.168.68.51/22`, gateway `192.168.68.1`
- `Ethernet`: `192.168.137.1/24` (auto-assigned by ICS)

### Raspberry Pi

- `wlan0`: `192.168.68.50/22`
- `eth0`: `192.168.137.2/24`

### Remote Server

- `34.13.59.163:8010`

---

## Required `multi_link.py` Link Settings

For Pi local source binding, use Pi interface IPs only:

- Link A (Ethernet path): bind `192.168.137.2`, target `34.13.59.163:8010`
- Link B (WiFi path): bind `192.168.68.50`, target `34.13.59.163:8010`

Example CLI form:

```bash
python3 src/py/links/multi_link.py \
  --link "eth0,192.168.137.2,34.13.59.163,8010" \
  --link "wlan0,192.168.68.50,34.13.59.163,8010" \
  -p 9010
```

---

## Windows ICS Sharing Setup (Done)

On Windows:

1. Open `ncpa.cpl`
2. Right-click `WiFi 3` -> `Properties`
3. `Sharing` tab
4. Enable: "Allow other network users to connect through this computer's Internet connection"
5. Select `Ethernet` as home network connection

Expected outcome:

- Windows Ethernet becomes `192.168.137.1/24`

---

## Pi Source-Based Routing (Policy Routing)

Use policy routing so each source IP exits the intended path:

```bash
# Clear stale rules/tables (ignore errors if absent)
sudo ip rule del from 192.168.2.188/32 table 100 2>/dev/null || true
sudo ip rule del from 192.168.68.50/32 table 101 2>/dev/null || true
sudo ip rule del from 192.168.137.2/32 table 100 2>/dev/null || true
sudo ip route flush table 100
sudo ip route flush table 101

# Table 100: eth0 via Windows ICS gateway
sudo ip route add 192.168.137.0/24 dev eth0 src 192.168.137.2 table 100
sudo ip route add default via 192.168.137.1 dev eth0 table 100
sudo ip rule add from 192.168.137.2/32 table 100 priority 100

# Table 101: wlan0 via WiFi router
sudo ip route add 192.168.68.0/22 dev wlan0 src 192.168.68.50 table 101
sudo ip route add default via 192.168.68.1 dev wlan0 table 101
sudo ip rule add from 192.168.68.50/32 table 101 priority 101

sudo ip route flush cache
```

---

## Verification Commands

### Route selection checks

```bash
ip route get 34.13.59.163 from 192.168.137.2
ip route get 34.13.59.163 from 192.168.68.50
```

Expected:

- `from 192.168.137.2` -> `via 192.168.137.1 dev eth0 table 100`
- `from 192.168.68.50` -> `via 192.168.68.1 dev wlan0 table 101`

### Connectivity checks

```bash
ping -c 3 192.168.137.1
nc -s 192.168.137.2 -vz 34.13.59.163 8010
nc -s 192.168.68.50 -vz 34.13.59.163 8010
```

Both `nc` checks must succeed for both links to be usable.

---

## How Bandwidth Is Used by `multi_link.py`

Current behavior is path selection per connection (link-based selection), not full packet-level bonding for a single TCP stream.

- Multiple client sessions can be distributed across both routes.
- True "same stream simultaneously on both links" would require fan-out/multipath application logic changes.

---

## Common Failure Signatures and Meaning

- `Errno 99 cannot assign requested address`:
  bind IP is not local to the Pi interface.
- `No route to host` from `nc -s ...`:
  route/gateway/NAT path for that source is broken.
- `Destination Host Unreachable` ping to gateway:
  L2 adjacency problem (cable/interface/subnet mismatch).

---

## Operational Runbook (Short)

1. Confirm Windows Ethernet is `192.168.137.1` (ICS active).
2. Confirm Pi eth0 is `192.168.137.2/24`.
3. Apply Pi source-based routing tables/rules.
4. Verify `ip route get` for both source IPs.
5. Verify `nc -s` to GCP on both sources.
6. Run `multi_link.py` with correct link source/target settings.

