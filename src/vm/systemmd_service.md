create the service
```
[Unit]
Description=TCP/UDP Echo Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/echo_server
ExecStart=/opt/echo_server/venv/bin/python /opt/echo_server/server.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
```

then enable the service
```
sudo systemctl daemon-reload
sudo systemctl enable echo-server
sudo systemctl start echo-server
sudo systemctl status echo-server --no-pager
```