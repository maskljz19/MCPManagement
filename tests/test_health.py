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
