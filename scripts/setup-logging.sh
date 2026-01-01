#!/bin/bash

# Setup log rotation for Docker containers
# This script should be run on the host system

set -e

echo "Setting up log rotation for MCP Platform containers..."

# Create logrotate configuration
sudo tee /etc/logrotate.d/mcp-platform > /dev/null <<EOF
/var/lib/docker/containers/*/*-json.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    postrotate
        docker kill --signal=USR1 \$(docker ps -q) 2>/dev/null || true
    endscript
}
EOF

# Set up Docker daemon logging configuration
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "3"
    }
}
EOF

echo "Log rotation configured successfully!"
echo "Please restart Docker daemon: sudo systemctl restart docker"