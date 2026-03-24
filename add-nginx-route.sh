#!/usr/bin/env bash
# add-nginx-route.sh — Add lloyds-insight-syndicate-analysis to host nginx
set -euo pipefail

CONF=/etc/nginx/sites-enabled/svralia01.conf

echo "==> Writing $CONF ..."
sudo tee "$CONF" > /dev/null << 'EOF'
server {
    listen 80;
    server_name svralia01.longtailre.com 10.0.1.4;

    location /uw-memo-writer/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /uw-memo-writer;
        proxy_read_timeout 300s;
        client_max_body_size 100M;
    }

    location /leap/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /leap;
        proxy_read_timeout 300s;
        client_max_body_size 100M;
    }

    location /nda-database/ {
        proxy_pass http://127.0.0.1:8002/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /nda-database;
        proxy_read_timeout 300s;
        client_max_body_size 100M;
    }

    location /lloyds-insight-syndicate-analysis/ {
        proxy_pass http://127.0.0.1:8502/lloyds-insight-syndicate-analysis/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
EOF

echo "==> Testing nginx config..."
sudo nginx -t

echo "==> Reloading nginx..."
sudo systemctl reload nginx

echo ""
echo "================================================================"
echo " App is live at:"
echo "   http://svralia01.longtailre.com/lloyds-insight-syndicate-analysis/"
echo "================================================================"
