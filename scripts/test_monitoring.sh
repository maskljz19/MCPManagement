#!/bin/bash
# Monitoring Test Script for MCP Platform Backend
# This script tests the monitoring infrastructure

set -e

echo "========================================="
echo "MCP Platform Monitoring Tests"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

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
    echo -e "${BLUE}ℹ $1${NC}"
}

print_test_header() {
    echo ""
    echo "----------------------------------------"
    echo "Test: $1"
    echo "----------------------------------------"
}

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    if eval "$test_command" > /dev/null 2>&1; then
        print_success "$test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        print_error "$test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Test 1: Service Health Checks
print_test_header "Service Health Checks"

run_test "Prometheus is running" "docker ps | grep -q mcp-prometheus"
run_test "Alertmanager is running" "docker ps | grep -q mcp-alertmanager"
run_test "Grafana is running" "docker ps | grep -q mcp-grafana"
run_test "Node Exporter is running" "docker ps | grep -q mcp-node-exporter"
run_test "Redis Exporter is running" "docker ps | grep -q mcp-redis-exporter"
run_test "MySQL Exporter is running" "docker ps | grep -q mcp-mysql-exporter"
run_test "MongoDB Exporter is running" "docker ps | grep -q mcp-mongodb-exporter"
run_test "Elasticsearch Exporter is running" "docker ps | grep -q mcp-elasticsearch-exporter"

# Test 2: Service Endpoints
print_test_header "Service Endpoint Availability"

run_test "Prometheus API is accessible" "curl -sf http://localhost:9090/-/healthy"
run_test "Alertmanager API is accessible" "curl -sf http://localhost:9093/-/healthy"
run_test "Grafana API is accessible" "curl -sf http://localhost:3000/api/health"
run_test "Node Exporter metrics endpoint" "curl -sf http://localhost:9100/metrics | grep -q node_"
run_test "Redis Exporter metrics endpoint" "curl -sf http://localhost:9121/metrics | grep -q redis_"
run_test "MySQL Exporter metrics endpoint" "curl -sf http://localhost:9104/metrics | grep -q mysql_"
run_test "MongoDB Exporter metrics endpoint" "curl -sf http://localhost:9216/metrics | grep -q mongodb_"
run_test "Elasticsearch Exporter metrics endpoint" "curl -sf http://localhost:9114/metrics | grep -q elasticsearch_"

# Test 3: Prometheus Configuration
print_test_header "Prometheus Configuration"

run_test "Prometheus config is loaded" "curl -sf http://localhost:9090/api/v1/status/config | grep -q prometheus"
run_test "Alert rules are loaded" "curl -sf http://localhost:9090/api/v1/rules | grep -q groups"

# Test 4: Prometheus Targets
print_test_header "Prometheus Target Status"

print_info "Checking Prometheus targets..."
targets_response=$(curl -s http://localhost:9090/api/v1/targets)

# Check if API target is up
if echo "$targets_response" | grep -q '"job":"mcp-platform-api"' && echo "$targets_response" | grep -q '"health":"up"'; then
    print_success "MCP Platform API target is up"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "MCP Platform API target is not up (may not be running)"
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Check if node-exporter target is up
if echo "$targets_response" | grep -q '"job":"node-exporter"' && echo "$targets_response" | grep -q '"health":"up"'; then
    print_success "Node Exporter target is up"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_error "Node Exporter target is not up"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 5: Metrics Collection
print_test_header "Metrics Collection"

print_info "Verifying metrics are being collected..."

# Query for system metrics
run_test "CPU metrics are collected" "curl -sf 'http://localhost:9090/api/v1/query?query=node_cpu_seconds_total' | grep -q '\"status\":\"success\"'"
run_test "Memory metrics are collected" "curl -sf 'http://localhost:9090/api/v1/query?query=node_memory_MemAvailable_bytes' | grep -q '\"status\":\"success\"'"
run_test "Disk metrics are collected" "curl -sf 'http://localhost:9090/api/v1/query?query=node_filesystem_avail_bytes' | grep -q '\"status\":\"success\"'"

# Query for database metrics
run_test "Redis metrics are collected" "curl -sf 'http://localhost:9090/api/v1/query?query=redis_memory_used_bytes' | grep -q '\"status\":\"success\"'"

# Test 6: Alert Rules
print_test_header "Alert Rules"

print_info "Checking alert rules..."
alerts_response=$(curl -s http://localhost:9090/api/v1/rules)

# Count alert rules
alert_count=$(echo "$alerts_response" | grep -o '"type":"alerting"' | wc -l)
print_info "Found $alert_count alert rules"

if [ "$alert_count" -gt 0 ]; then
    print_success "Alert rules are loaded"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_error "No alert rules found"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Check for specific alert rules
run_test "HighExecutionErrorRate alert exists" "echo '$alerts_response' | grep -q 'HighExecutionErrorRate'"
run_test "HighQueueDepth alert exists" "echo '$alerts_response' | grep -q 'HighQueueDepth'"
run_test "LowCacheHitRate alert exists" "echo '$alerts_response' | grep -q 'LowCacheHitRate'"
run_test "ServiceDown alert exists" "echo '$alerts_response' | grep -q 'ServiceDown'"

# Test 7: Alertmanager Configuration
print_test_header "Alertmanager Configuration"

run_test "Alertmanager config is loaded" "curl -sf http://localhost:9093/api/v2/status | grep -q 'config'"
run_test "Alertmanager has receivers configured" "curl -sf http://localhost:9093/api/v2/status | grep -q 'receivers'"

# Test 8: Grafana Configuration
print_test_header "Grafana Configuration"

# Get Grafana datasources
print_info "Checking Grafana datasources..."
datasources_response=$(curl -s -u admin:admin http://localhost:3000/api/datasources)

if echo "$datasources_response" | grep -q '"name":"Prometheus"'; then
    print_success "Prometheus datasource is configured"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_error "Prometheus datasource is not configured"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Get Grafana dashboards
print_info "Checking Grafana dashboards..."
dashboards_response=$(curl -s -u admin:admin http://localhost:3000/api/search?type=dash-db)

dashboard_count=$(echo "$dashboards_response" | grep -o '"type":"dash-db"' | wc -l)
print_info "Found $dashboard_count dashboards"

if [ "$dashboard_count" -ge 2 ]; then
    print_success "Dashboards are loaded (expected: 2, found: $dashboard_count)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "Expected 2 dashboards, found: $dashboard_count"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 9: Dashboard Validation
print_test_header "Dashboard Validation"

if echo "$dashboards_response" | grep -q "MCP Execution"; then
    print_success "MCP Execution Monitoring dashboard exists"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_error "MCP Execution Monitoring dashboard not found"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

if echo "$dashboards_response" | grep -q "System Overview"; then
    print_success "System Overview dashboard exists"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_error "System Overview dashboard not found"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 10: Alert Testing (Optional - requires triggering conditions)
print_test_header "Alert Testing"

print_info "Checking for active alerts..."
active_alerts=$(curl -s http://localhost:9090/api/v1/alerts | grep -o '"state":"firing"' | wc -l)

if [ "$active_alerts" -eq 0 ]; then
    print_success "No active alerts (system is healthy)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "$active_alerts alerts are currently firing"
    print_info "This may be expected depending on system state"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 11: Data Retention
print_test_header "Data Retention"

print_info "Checking Prometheus data retention..."
retention_info=$(curl -s http://localhost:9090/api/v1/status/runtimeinfo)

if echo "$retention_info" | grep -q "storageRetention"; then
    retention=$(echo "$retention_info" | grep -o '"storageRetention":"[^"]*"' | cut -d'"' -f4)
    print_success "Data retention is configured: $retention"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "Could not determine data retention setting"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Test 12: Performance Check
print_test_header "Performance Check"

print_info "Testing query performance..."
start_time=$(date +%s%N)
curl -sf 'http://localhost:9090/api/v1/query?query=up' > /dev/null
end_time=$(date +%s%N)
query_time=$(( (end_time - start_time) / 1000000 ))

if [ "$query_time" -lt 1000 ]; then
    print_success "Query performance is good (${query_time}ms)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    print_warning "Query performance is slow (${query_time}ms)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
TESTS_TOTAL=$((TESTS_TOTAL + 1))

# Summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo ""
echo "Total Tests:  $TESTS_TOTAL"
echo -e "${GREEN}Passed:       $TESTS_PASSED${NC}"
echo -e "${RED}Failed:       $TESTS_FAILED${NC}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    print_success "All tests passed! Monitoring is working correctly."
    echo ""
    echo "Next steps:"
    echo "  1. Access Grafana: http://localhost:3000"
    echo "  2. View dashboards: MCP Execution Monitoring, System Overview"
    echo "  3. Configure alert notifications in alertmanager.yml"
    echo "  4. Monitor your application metrics"
    exit 0
else
    print_error "Some tests failed. Please review the output above."
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check service logs: docker-compose logs [service]"
    echo "  2. Verify configuration files"
    echo "  3. Ensure all services are running: docker-compose ps"
    echo "  4. Review MONITORING_SETUP_GUIDE.md"
    exit 1
fi
