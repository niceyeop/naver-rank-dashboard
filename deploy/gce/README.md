# Google Compute Engine Setup

## Files

- `naver-rank-dashboard.service`: Streamlit dashboard service template
- `naver-rank-collector.service`: collector loop service template
- `install-systemd.sh`: helper script to install both unit files

## Server bootstrap

Clone the repository on the VM and create the app environment:

```bash
git clone <repo-url> /home/ubuntu/naver-rank-dashboard
cd /home/ubuntu/naver-rank-dashboard
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Create the runtime config:

```bash
cp .env.example .env
```

Install the services:

```bash
chmod +x deploy/gce/install-systemd.sh
./deploy/gce/install-systemd.sh /home/ubuntu/naver-rank-dashboard ubuntu
```

## Notes

- If the VM user or app path differs, pass them as arguments to `install-systemd.sh`.
- The GitHub Actions workflow should use the same path as `GCE_APP_DIR`.
- If you expose the dashboard publicly, restrict the firewall to the intended port.
