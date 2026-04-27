# GitHub to Naver Cloud Auto Deploy

This project can be deployed with the simplest setup:

- push to `main`
- GitHub Actions connects to the Naver Cloud server over SSH
- the server pulls the latest code, installs Python packages, and restarts the dashboard service

## 1. Prepare the Naver Cloud server

Example server path:

```bash
sudo mkdir -p /opt/naver-rank-dashboard
sudo chown -R $USER:$USER /opt/naver-rank-dashboard
cd /opt
git clone https://github.com/niceyeop/naver-rank-dashboard.git
cd /opt/naver-rank-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
chmod +x deploy/deploy.sh deploy/run_dashboard.sh
```

If the repository is private, clone with an account or token that has access.

## 2. Create the systemd service

Copy the example service:

```bash
sudo cp deploy/naver-rank-dashboard.service.example /etc/systemd/system/naver-rank-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable naver-rank-dashboard
sudo systemctl start naver-rank-dashboard
```

Check status:

```bash
sudo systemctl status naver-rank-dashboard
```

## 3. Allow restart without interactive sudo

Open sudoers safely:

```bash
sudo visudo
```

Add this line:

```text
ubuntu ALL=NOPASSWD:/bin/systemctl restart naver-rank-dashboard,/bin/systemctl status naver-rank-dashboard --no-pager
```

If your server user is not `ubuntu`, replace it with the actual user.

## 4. Add GitHub repository secrets

In GitHub repository settings, add:

- `NCP_HOST`: server public IP or domain
- `NCP_USER`: SSH user, for example `ubuntu`
- `NCP_SSH_KEY`: private SSH key contents
- `NCP_APP_DIR`: deployment path, for example `/opt/naver-rank-dashboard`
- `NCP_SERVICE_NAME`: `naver-rank-dashboard`
- `NCP_APP_PORT`: optional, default is `8501`

If SSH is not using port `22`, change the workflow file and add `port: YOUR_PORT` in `.github/workflows/deploy.yml`.

## 5. What happens on each push

The workflow at `.github/workflows/deploy.yml` runs on every push to `main`.

It does this:

1. Connect to the Naver Cloud server with SSH
2. Run `deploy/deploy.sh`
3. Pull the latest commit
4. Install dependencies into `.venv`
5. Restart the systemd service

## 6. Open the dashboard

If the server firewall and Naver Cloud ACG allow inbound traffic on the app port, open:

```text
http://YOUR_SERVER_IP:8501
```

If you want a domain or HTTPS, put Nginx in front later. The deployment workflow can stay the same.
