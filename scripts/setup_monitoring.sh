#!/bin/bash
# Monitoring Setup Script for MCP Platform Backend
# This script sets up Prometheus, Grafana, and Alertmanager monitoring

set -e

echo "========================================="
echo "MCP Platform Monitoring Setup"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "$1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi
print_success "Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi
print_success "docker-compose is available"

# Check if required configuration files exist
print_info "Checking configuration files..."

required_files=(
    "prometheus.yml"
    "prometheus-alerts.yml"
    "alertmanager.yml"
    "grafana-provisioning-datasources.yml"
    "grafana-provisioning-dashboards.yml"
    "grafana-dashboard-mcp-executions.json"
    "grafana-dashboard-system-overview.json"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        print_error "Required file not found: $file"
        exit 1
    fi
done
print_success "All configuration files found"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Created .env file from .env.example"
        print_warning "Please update .env file with your configuration before continuing"
        exit 0
    else
        print_error ".env.example file not found"
        exit 1
    fi
fi
print_success ".env file found"

# Load environment variables
source .env

# Validate Alertmanager configuration
print_info "Validating Alertmanager configuration..."
if docker run --rm -v "$(pwd)/alertmanager.yml:/etc/alertmanager/alertmanager.yml" prom/alertmanager:v0.26.0 amtool check-config /etc/alertmanager/alertmanager.yml > /dev/null 2>&1; then
    print_success "Alertmanager configuration is valid"
else
    print_error "Alertmanager configuration is invalid"
    print_info "Run: docker run --rm -v \$(pwd)/alertmanager.yml:/etc/alertmanager/alertmanager.yml prom/alertmanager:v0.26.0 amtool check-config /etc/alertmanager/alertmanager.yml"
    exit 1
fi

# Validate Prometheus configuration
print_info "Validating Prometheus configuration..."
if docker run --rm -v "$(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml" -v "$(pwd)/prometheus-alerts.yml:/etc/prometheus/alerts/alerts.yml" prom/prometheus:v2.48.0 promtool check config /etc/prometheus/prometheus.yml > /dev/null 2>&1; then
    print_success "Prometheus configuration is valid"
else
    print_error "Prometheus configuration is invalid"
    print_info "Run: docker run --rm -v \$(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus:v2.48.0 promtool check config /etc/prometheus/prometheus.yml"
    exit 1
fi

# Start monitoring services
print_info ""
print_info "Starting monitoring services..."
print_info ""

# Start Prometheus
print_info "Starting Prometheus..."
docker-compose up -d prometheus
sleep 5
if docker ps | grep -q mcp-prometheus; then
    print_success "Prometheus started successfully"
else
    print_error "Failed to start Prometheus"
    exit 1
fi

# Start Alertmanager
print_info "Starting Alertmanager..."
docker-compose up -d alertmanager
sleep 5
if docker ps | grep -q mcp-alertmanager; then
    print_success "Alertmanager started successfully"
else
    print_error "Failed to start Alertmanager"
    exit 1
fi

# Start Grafana
print_info "Starting Grafana..."
docker-compose up -d grafana
sleep 10
if docker ps | grep -q mcp-grafana; then
    print_success "Grafana started successfully"
else
    print_error "Failed to start Grafana"
    exit 1
fi

# Start exporters
print_info "Starting exporters..."
docker-compose up -d node-exporter redis-exporter mysql-exporter mongodb-exporter elasticsearch-exporter
sleep 5
print_success "Exporters started successfully"

# Wait for services to be healthy
print_info ""
print_info "Waiting for services to be healthy..."
print_info ""

max_wait=60
wait_time=0

# Wait for Prometheus
while [ $wait_time -lt $max_wait ]; do
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        print_success "Prometheus is healthy"
        break
    fi
    sleep 2
    wait_time=$((wait_time + 2))
done

if [ $wait_time -ge $max_wait ]; then
    print_error "Prometheus health check timeout"
    exit 1
fi

# Wait for Alertmanager
wait_time=0
while [ $wait_time -lt $max_wait ]; do
    if curl -s http://localhost:9093/-/healthy > /dev/null 2>&1; then
        print_success "Alertmanager is healthy"
        break
    fi
    sleep 2
    wait_time=$((wait_time + 2))
done

if [ $wait_time -ge $max_wait ]; then
    print_error "Alertmanager health check timeout"
    exit 1
fi

# Wait for Grafana
wait_time=0
while [ $wait_time -lt $max_wait ]; do
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        print_success "Grafana is healthy"
        break
    fi
    sleep 2
    wait_time=$((wait_time + 2))
done

if [ $wait_time -ge $max_wait ]; then
    print_error "Grafana health check timeout"
    exit 1
fi

# Display service URLs
print_info ""
print_info "========================================="
print_info "Monitoring Setup Complete!"
print_info "========================================="
print_info ""
print_info "Service URLs:"
print_info "  Prometheus:    http://localhost:9090"
print_info "  Alertmanager:  http://localhost:9093"
print_info "  Grafana:       http://localhost:3000"
print_info ""
print_info "Grafana Credentials:"
print_info "  Username: ${GRAFANA_ADMIN_USER:-admin}"
print_info "  Password: ${GRAFANA_ADMIN_PASSWORD:-admin}"
print_info ""
print_info "Exporters:"
print_info "  Node Exporter:          http://localhost:9100/metrics"
print_info "  Redis Exporter:         http://localhost:9121/metrics"
print_info "  MySQL Exporter:         http://localhost:9104/metrics"
print_info "  MongoDB Exporter:       http://localhost:9216/metrics"
print_info "  Elasticsearch Exporter: http://localhost:9114/metrics"
print_info ""
print_info "Pre-configured Dashboards:"
print_info "  - MCP Execution Monitoring"
print_info "  - System Overview"
print_info ""
print_warning "Note: Update alertmanager.yml with your notification channels (email, Slack, PagerDuty)"
print_info ""
print_success "Monitoring is now active!"
