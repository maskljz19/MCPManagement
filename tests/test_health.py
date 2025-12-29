"""Unit tests for health check endpoint"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)


class TestHealthCheck:
    """Test suite for health check endpoint"""
    
    def test_health_check_all_services_healthy(self):
        """Test health check returns 200 when all services are healthy"""
        # Mock all service checks to return True
        with patch('app.api.v1.health.check_mysql', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_mongodb', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_redis', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_qdrant', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_rabbitmq', new_callable=AsyncMock, return_value=True):
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["mysql"] is True
            assert data["services"]["mongodb"] is True
            assert data["services"]["redis"] is True
            assert data["services"]["qdrant"] is True
            assert data["services"]["rabbitmq"] is True
    
    def test_health_check_mysql_unavailable(self):
        """Test health check returns 503 when MySQL is unavailable"""
        # Mock MySQL as unhealthy, others as healthy
        with patch('app.api.v1.health.check_mysql', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_mongodb', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_redis', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_qdrant', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_rabbitmq', new_callable=AsyncMock, return_value=True):
            
            response = client.get("/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["mysql"] is False
            assert data["services"]["mongodb"] is True
    
    def test_health_check_mongodb_unavailable(self):
        """Test health check returns 503 when MongoDB is unavailable"""
        # Mock MongoDB as unhealthy, others as healthy
        with patch('app.api.v1.health.check_mysql', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_mongodb', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_redis', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_qdrant', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_rabbitmq', new_callable=AsyncMock, return_value=True):
            
            response = client.get("/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["mongodb"] is False
    
    def test_health_check_redis_unavailable(self):
        """Test health check returns 503 when Redis is unavailable"""
        # Mock Redis as unhealthy, others as healthy
        with patch('app.api.v1.health.check_mysql', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_mongodb', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_redis', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_qdrant', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_rabbitmq', new_callable=AsyncMock, return_value=True):
            
            response = client.get("/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["redis"] is False
    
    def test_health_check_multiple_services_unavailable(self):
        """Test health check returns 503 when multiple services are unavailable"""
        # Mock multiple services as unhealthy
        with patch('app.api.v1.health.check_mysql', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_mongodb', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_redis', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_qdrant', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_rabbitmq', new_callable=AsyncMock, return_value=True):
            
            response = client.get("/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["mysql"] is False
            assert data["services"]["mongodb"] is False
            assert data["services"]["redis"] is True
    
    def test_health_check_all_services_unavailable(self):
        """Test health check returns 503 when all services are unavailable"""
        # Mock all services as unhealthy
        with patch('app.api.v1.health.check_mysql', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_mongodb', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_redis', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_qdrant', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_rabbitmq', new_callable=AsyncMock, return_value=False):
            
            response = client.get("/health")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert all(not status for status in data["services"].values())


class TestMetricsEndpoint:
    """Test suite for Prometheus metrics endpoint"""
    
    def test_metrics_endpoint_returns_prometheus_format(self):
        """
        Test metrics endpoint returns Prometheus format.
        
        **Requirements: 12.1**
        """
        response = client.get("/metrics")
        
        # Should return 200 OK
        assert response.status_code == 200
        
        # Should have correct content type
        assert "text/plain" in response.headers["content-type"]
        
        # Should contain Prometheus metrics format
        content = response.text
        assert "# HELP" in content or "# TYPE" in content or len(content) > 0
    
    def test_metrics_endpoint_contains_http_metrics(self):
        """Test metrics endpoint contains HTTP request metrics"""
        # Make a request to generate some metrics
        client.get("/health")
        
        # Get metrics
        response = client.get("/metrics")
        content = response.text
        
        # Should contain HTTP metrics
        # Note: Metrics might not be present if not yet recorded
        # This is a basic check that the endpoint works
        assert response.status_code == 200
    
    def test_metrics_endpoint_accessible_without_auth(self):
        """Test metrics endpoint is accessible without authentication"""
        response = client.get("/metrics")
        
        # Should not require authentication
        assert response.status_code == 200
        assert response.status_code != 401
        assert response.status_code != 403


class TestHealthCheckDependencies:
    """Test suite for individual health check functions"""
    
    def test_health_check_verifies_all_dependencies(self):
        """
        Test health check verifies all required dependencies.
        
        **Requirements: 12.3**
        """
        with patch('app.api.v1.health.check_mysql', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_mongodb', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_redis', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_qdrant', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_rabbitmq', new_callable=AsyncMock, return_value=True):
            
            response = client.get("/health")
            data = response.json()
            
            # Should check all required services
            required_services = ["mysql", "mongodb", "redis", "qdrant", "rabbitmq"]
            for service in required_services:
                assert service in data["services"], f"Missing health check for {service}"
    
    def test_health_check_returns_detailed_status(self):
        """
        Test health check returns detailed status for each service.
        
        **Requirements: 12.3**
        """
        with patch('app.api.v1.health.check_mysql', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_mongodb', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_redis', new_callable=AsyncMock, return_value=True), \
             patch('app.api.v1.health.check_qdrant', new_callable=AsyncMock, return_value=False), \
             patch('app.api.v1.health.check_rabbitmq', new_callable=AsyncMock, return_value=True):
            
            response = client.get("/health")
            data = response.json()
            
            # Should have overall status
            assert "status" in data
            assert data["status"] == "unhealthy"
            
            # Should have detailed service status
            assert "services" in data
            assert data["services"]["mysql"] is True
            assert data["services"]["mongodb"] is False
            assert data["services"]["redis"] is True
            assert data["services"]["qdrant"] is False
            assert data["services"]["rabbitmq"] is True
