#!/usr/bin/env bash
# One-shot droplet bootstrap: swap, clone repo, write .env, build & start.
# Run on the droplet as root:  bash setup-droplet.sh
set -euo pipefail

REPO="https://github.com/FiscalMindset/web3.git"
DIR=/opt/web3-tutor

# 2G swap — Next.js build needs it on small droplets
if ! swapon --show | grep -q swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if [ ! -d "$DIR" ]; then
  git clone "$REPO" "$DIR"
else
  git -C "$DIR" pull
fi

cd "$DIR"

if [ ! -f .env ]; then
  echo "ERROR: create $DIR/.env first (base_url=…, api_key=…, model=…)" >&2
  exit 1
fi

docker compose up -d --build
docker compose ps
echo "✅ live on http://$(curl -s ifconfig.me)/"
