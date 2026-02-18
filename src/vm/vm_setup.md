VM one time set up
```
sudo mkdir -p /opt/echo_server
sudo chown -R $USER:$USER /opt/echo_server

sudo apt-get update
sudo apt-get install -y python3 python3-venv rsync
python3 -m venv /opt/echo_server/venv
/opt/echo_server/venv/bin/pip install --upgrade pip
```