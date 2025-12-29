"""Integration tests for authentication endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import UserModel, UserRole
from app.models.api_key import APIKeyModel
from app.core.security import hash_password, verify_api_key
from uuid import uuid4


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful user registration"""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123",
        "role": "viewer"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["role"] == "viewer"
    assert "id" in data
    assert "password" not in data  # Password should not be in response
    
    # Verify user was created in database
    stmt = select(UserModel).where(UserModel.username == "testuser")
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == "test@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, db_session: AsyncSession):
    """Test registration with duplicate username fails"""
    # Create existing user
    existing_user = UserModel(
        id=str(uuid4()),
        username="existing",
        email="existing@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.VIEWER
    )
    db_session.add(existing_user)
    await db_session.commit()
    
    # Try to register with same username
    user_data = {
        "username": "existing",
        "email": "different@example.com",
        "password": "TestPass123"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful login with valid credentials"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="loginuser",
        email="login@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    credentials = {
        "username": "loginuser",
        "password": "TestPass123"
    }
    
    response = await client.post("/api/v1/auth/login", json=credentials)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_with_email(client: AsyncClient, db_session: AsyncSession):
    """Test login using email instead of username"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="emailuser",
        email="email@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.VIEWER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login with email
    credentials = {
        "username": "email@example.com",  # Using email in username field
        "password": "TestPass123"
    }
    
    response = await client.post("/api/v1/auth/login", json=credentials)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, db_session: AsyncSession):
    """Test login with invalid credentials fails"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="validuser",
        email="valid@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.VIEWER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Try to login with wrong password
    credentials = {
        "username": "validuser",
        "password": "WrongPassword"
    }
    
    response = await client.post("/api/v1/auth/login", json=credentials)
    
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession):
    """Test login with inactive user fails"""
    # Create inactive user
    user = UserModel(
        id=str(uuid4()),
        username="inactive",
        email="inactive@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.VIEWER,
        is_active=False
    )
    db_session.add(user)
    await db_session.commit()
    
    # Try to login
    credentials = {
        "username": "inactive",
        "password": "TestPass123"
    }
    
    response = await client.post("/api/v1/auth/login", json=credentials)
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful token refresh"""
    # Create test user and login
    user = UserModel(
        id=str(uuid4()),
        username="refreshuser",
        email="refresh@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login to get tokens
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "refreshuser",
        "password": "TestPass123"
    })
    tokens = login_response.json()
    refresh_token = tokens["refresh_token"]
    
    # Refresh access token
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    # New access token should be different from original
    assert data["access_token"] != tokens["access_token"]


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """Test refresh with invalid token fails"""
    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid_token_here"
    })
    
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful logout"""
    # Create test user and login
    user = UserModel(
        id=str(uuid4()),
        username="logoutuser",
        email="logout@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.VIEWER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "logoutuser",
        "password": "TestPass123"
    })
    tokens = login_response.json()
    
    # Logout
    response = await client.post("/api/v1/auth/logout", json={
        "refresh_token": tokens["refresh_token"]
    })
    
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_create_api_key_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful API key creation"""
    # Create test user and login
    user = UserModel(
        id=str(uuid4()),
        username="apikeyuser",
        email="apikey@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login to get access token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "apikeyuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Create API key
    response = await client.post(
        "/api/v1/auth/api-keys",
        json={"name": "Test API Key"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test API Key"
    assert "key" in data  # Plain key should be returned once
    assert "id" in data
    assert len(data["key"]) == 64  # 32 bytes hex = 64 characters
    
    # Verify API key was created in database
    stmt = select(APIKeyModel).where(APIKeyModel.user_id == user.id)
    result = await db_session.execute(stmt)
    api_key = result.scalar_one_or_none()
    assert api_key is not None
    assert api_key.name == "Test API Key"
    # Verify the plain key matches the hash
    assert verify_api_key(data["key"], api_key.key_hash)


@pytest.mark.asyncio
async def test_create_api_key_unauthorized(client: AsyncClient):
    """Test API key creation without authentication fails"""
    response = await client.post(
        "/api/v1/auth/api-keys",
        json={"name": "Test API Key"}
    )
    
    assert response.status_code == 403  # No authorization header


@pytest.mark.asyncio
async def test_list_api_keys(client: AsyncClient, db_session: AsyncSession):
    """Test listing user's API keys"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="listuser",
        email="list@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create some API keys
    from app.core.security import hash_api_key
    api_key1 = APIKeyModel(
        id=str(uuid4()),
        user_id=user.id,
        key_hash=hash_api_key("key1"),
        name="Key 1"
    )
    api_key2 = APIKeyModel(
        id=str(uuid4()),
        user_id=user.id,
        key_hash=hash_api_key("key2"),
        name="Key 2"
    )
    db_session.add(api_key1)
    db_session.add(api_key2)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "listuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # List API keys
    response = await client.get(
        "/api/v1/auth/api-keys",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(k["name"] == "Key 1" for k in data)
    assert any(k["name"] == "Key 2" for k in data)
    # Plain keys should not be in list response
    assert all("key" not in k for k in data)


@pytest.mark.asyncio
async def test_revoke_api_key(client: AsyncClient, db_session: AsyncSession):
    """Test revoking an API key"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="revokeuser",
        email="revoke@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create API key
    from app.core.security import hash_api_key
    api_key = APIKeyModel(
        id=str(uuid4()),
        user_id=user.id,
        key_hash=hash_api_key("testkey"),
        name="To Revoke"
    )
    db_session.add(api_key)
    await db_session.commit()
    key_id = api_key.id
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "revokeuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Revoke API key
    response = await client.delete(
        f"/api/v1/auth/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 204
    
    # Verify key was revoked in database
    await db_session.refresh(api_key)
    assert api_key.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_api_key_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test revoking non-existent API key fails"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="notfounduser",
        email="notfound@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "notfounduser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Try to revoke non-existent key
    fake_key_id = uuid4()
    response = await client.delete(
        f"/api/v1/auth/api-keys/{fake_key_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_key_usage_flow(client: AsyncClient, db_session: AsyncSession):
    """Test complete API key creation and usage flow"""
    # Create test user and login
    user = UserModel(
        id=str(uuid4()),
        username="flowuser",
        email="flow@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "flowuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Create API key
    create_response = await client.post(
        "/api/v1/auth/api-keys",
        json={"name": "Flow Test Key"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert create_response.status_code == 201
    plain_key = create_response.json()["key"]
    
    # Verify the key can be used for authentication
    # (This would be tested in actual API endpoint tests that accept API key auth)
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session=db_session, cache=None)
    authenticated_user = await auth_service.authenticate_api_key(plain_key)
    assert authenticated_user is not None
    assert authenticated_user.id == user.id

