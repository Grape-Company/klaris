#!/usr/bin/env bash
set -euo pipefail

# Self-hosted GitHub Actions Runner setup for VPS
# Usage:
#   1. Go to GitHub repo: Settings > Actions > Runners > New self-hosted runner
#   2. Copy the token and download URL
#   3. Run: sudo bash scripts/setup-runner.sh <TOKEN> [RUNNER_USER]
#
# Example:
#   sudo bash scripts/setup-runner.sh ABCDEF1234 github-runner

if [ $# -lt 1 ]; then
  echo "Usage: $0 <GITHUB_TOKEN> [RUNNER_USER]"
  echo "  GITHUB_TOKEN  - Token from GitHub repo Settings > Actions > Runners"
  echo "  RUNNER_USER   - User to run the runner (default: github-runner)"
  exit 1
fi

TOKEN="$1"
RUNNER_USER="${2:-github-runner}"
RUNNER_DIR="/home/${RUNNER_USER}/actions-runner"
DEPLOY_DIR="/opt/klaris"
GITHUB_ORG="Grape-Company"
GITHUB_REPO="klaris"
RUNNER_VERSION="2.322.0"

echo "=== Setting up GitHub Actions Self-Hosted Runner ==="
echo "Runner user: ${RUNNER_USER}"
echo "Runner dir:  ${RUNNER_DIR}"
echo "Deploy dir:  ${DEPLOY_DIR}"
echo ""

# --- Create runner user ---
if ! id "${RUNNER_USER}" &>/dev/null; then
  echo "Creating user: ${RUNNER_USER}"
  useradd -m -s /bin/bash "${RUNNER_USER}"
fi

# --- Install dependencies ---
echo "Installing dependencies..."
apt-get update -qq
apt-get install -y -qq curl jq docker-compose-plugin 2>/dev/null || true

# Check docker
if ! command -v docker &>/dev/null; then
  echo "ERROR: Docker is not installed. Install Docker first:"
  echo "  curl -fsSL https://get.docker.com | bash"
  exit 1
fi

# Add runner user to docker group
usermod -aG docker "${RUNNER_USER}"

# --- Setup runner (as runner user) ---
mkdir -p "${RUNNER_DIR}"
chown "${RUNNER_USER}:${RUNNER_USER}" "${RUNNER_DIR}"

if [ ! -f "${RUNNER_DIR}/run.sh" ]; then
  echo "Downloading GitHub Actions runner v${RUNNER_VERSION}..."
  DOWNLOAD_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"
  curl -fsSL "${DOWNLOAD_URL}" -o /tmp/runner.tar.gz
  tar xzf /tmp/runner.tar.gz -C "${RUNNER_DIR}"
  rm /tmp/runner.tar.gz
  chown -R "${RUNNER_USER}:${RUNNER_USER}" "${RUNNER_DIR}"
fi

echo "Configuring runner..."
sudo -u "${RUNNER_USER}" "${RUNNER_DIR}/config.sh" \
  --url "https://github.com/${GITHUB_ORG}/${GITHUB_REPO}" \
  --token "${TOKEN}" \
  --name "$(hostname)-runner" \
  --labels "vps,production" \
  --replace \
  --unattended

# --- Install as service ---
echo "Installing runner as systemd service..."
"${RUNNER_DIR}/svc.sh" install "${RUNNER_USER}"
"${RUNNER_DIR}/svc.sh" start

echo "Runner service status:"
"${RUNNER_DIR}/svc.sh" status

# --- Clone repo to deploy directory ---
if [ ! -d "${DEPLOY_DIR}/.git" ]; then
  echo "Cloning repo to ${DEPLOY_DIR}..."
  mkdir -p "$(dirname "${DEPLOY_DIR}")"
  git clone "https://github.com/${GITHUB_ORG}/${GITHUB_REPO}.git" "${DEPLOY_DIR}"
  chown -R "${RUNNER_USER}:${RUNNER_USER}" "${DEPLOY_DIR}"
else
  echo "Repo already exists at ${DEPLOY_DIR}, skipping clone."
fi

# --- Create .env from example if missing ---
if [ ! -f "${DEPLOY_DIR}/.env" ]; then
  echo "Creating .env from .env.example..."
  cp "${DEPLOY_DIR}/.env.example" "${DEPLOY_DIR}/.env"
  echo ""
  echo "WARNING: .env created from example. Edit ${DEPLOY_DIR}/.env with real secrets."
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit ${DEPLOY_DIR}/.env with your secrets (API keys, DB passwords)"
echo "  2. Verify docker is running: docker ps"
echo "  3. The workflow in .github/workflows/deploy.yml will run on push to main"
echo "  4. Check runner status: sudo ${RUNNER_DIR}/svc.sh status"
