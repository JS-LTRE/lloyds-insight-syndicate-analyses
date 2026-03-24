#!/usr/bin/env bash
# deploy.sh — Deploy Lloyd's Syndicate Explorer behind nginx
# Serves the app at: http://<server-ip>/lloyds-insight-syndicate-analysis/
set -euo pipefail

APP_PATH="lloyds-insight-syndicate-analysis"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

echo "==> Writing nginx config..."
mkdir -p nginx

cat > nginx/nginx.conf << 'EOF'
events {}

http {
    server {
        listen 80;

        location /lloyds-insight-syndicate-analysis/ {
            proxy_pass         http://streamlit:8501/lloyds-insight-syndicate-analysis/;
            proxy_http_version 1.1;

            proxy_set_header   Host              $host;
            proxy_set_header   X-Real-IP         $remote_addr;
            proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;

            # Required for Streamlit websockets
            proxy_set_header   Upgrade    $http_upgrade;
            proxy_set_header   Connection "upgrade";

            proxy_read_timeout 86400;
        }

        # Redirect bare root to the app
        location = / {
            return 301 /lloyds-insight-syndicate-analysis/;
        }
    }
}
EOF

echo "==> Writing docker-compose.yml..."
cat > docker-compose.yml << EOF
version: "3.9"

services:
  streamlit:
    build: .
    container_name: lloyds-insight-syndicate-analysis-app
    expose:
      - "8501"
    restart: unless-stopped
    command:
      - streamlit
      - run
      - syndicate_explorer.py
      - --server.port=8501
      - --server.address=0.0.0.0
      - --server.headless=true
      - --server.baseUrlPath=/${APP_PATH}
      - --browser.gatherUsageStats=false

  nginx:
    image: nginx:1.27-alpine
    container_name: lloyds-insight-syndicate-analysis-nginx
    ports:
      - "8502:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - streamlit
    restart: unless-stopped
EOF

echo "==> Building and starting containers..."
docker compose up --build -d

echo ""
echo "==> Waiting for app to become healthy (up to 60s)..."
for i in $(seq 1 12); do
    if curl -sf "http://localhost:8502/_stcore/health" > /dev/null 2>&1 || \
       curl -sf "http://localhost:8502/${APP_PATH}/_stcore/health" > /dev/null 2>&1; then
        echo "    Health check passed."
        break
    fi
    echo "    Attempt $i/12 — waiting 5s..."
    sleep 5
done

echo ""
echo "==> Container status:"
docker compose ps

echo ""
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "================================================================"
echo " App is live at:"
echo "   http://${SERVER_IP}:8502/${APP_PATH}/"
echo "================================================================"
