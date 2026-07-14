# Option A backend - refresh price data from a small VPS

The short-term refresh runs on Adil's PC (`refresh-data.bat`), so the data is only
fresh when that PC is on. Option A moves it to a ~5 EUR/month VPS with its own IP:
the VPS rebuilds the 4 datasets every 4h and pushes them here, and the app keeps
pulling this repo exactly as today. **No app change** - the app never talks to the
VPS, only to this repo's raw files.

Why a VPS and not GitHub Actions: AODP rate-limits by request rate, not by blocking
datacenters. A **dedicated** VPS IP at the builders' 2s pace serves cleanly (tested).
GitHub Actions failed because its **shared** IP pool is hammered by other scrapers,
pushing it over AODP's limit, and the job died at the 45-min timeout.

## Setup (Ubuntu VPS, ~15 min)

1. Rent the smallest VPS (Hetzner CX22 ~4 EUR, or any 1 vCPU / 1 GB). Ubuntu 22.04+.
2. Install deps and clone:
   ```
   sudo apt update && sudo apt install -y python3 git
   git clone https://github.com/AdilOkay/city-buy-list-data.git
   cd city-buy-list-data
   ```
3. **Probe first** (confirm this provider's IP is not throttled):
   ```
   python3 deploy/probe.py
   ```
   Expect `VERDICT: OK`. If it says THROTTLED, destroy the VPS (you have paid cents)
   and try another provider, or go to option B.
4. Give the VPS push rights via a **deploy key** (write):
   ```
   ssh-keygen -t ed25519 -C "cbl-vps" -f ~/.ssh/cbl_deploy -N ""
   cat ~/.ssh/cbl_deploy.pub
   ```
   Add that public key in the repo: **Settings -> Deploy keys -> Add deploy key ->
   Allow write access**. Then switch the clone to SSH + point git at the key:
   ```
   git remote set-url origin git@github.com:AdilOkay/city-buy-list-data.git
   git config core.sshCommand "ssh -i ~/.ssh/cbl_deploy -o IdentitiesOnly=yes"
   git config user.name "cbl-vps" && git config user.email "cbl-vps@local"
   ```
5. Test one real run end-to-end (~20-30 min), check it pushed:
   ```
   bash deploy/refresh.sh && tail -5 deploy/refresh.log
   ```
6. Install the cron (every 4h at :10 UTC):
   ```
   ( crontab -l 2>/dev/null; echo "10 */4 * * * cd $HOME/city-buy-list-data && bash deploy/refresh.sh" ) | crontab -
   ```
7. **Disable the PC stopgap** so there is a single writer:
   Windows -> `schtasks /delete /tn CBL_DataRefresh /f`.

Done. Fresh data every 4h, independent of any PC. Cost = the VPS only.

## Notes
- Cadence: 4h matches AFM. Do not go below ~1h (respect AODP; the run itself is ~25 min).
- If AODP ever throttles the VPS IP later, either slow the cron or move to option B
  (subscribe to the AODP real-time NATS stream instead of polling the REST API).
- Alternative to push-to-repo: serve `docs/data/` over nginx and point the app's
  `DATA_BASE` at the VPS URL. More moving parts (web server + HTTPS); push-to-repo is
  simpler and uses GitHub's CDN for free.
