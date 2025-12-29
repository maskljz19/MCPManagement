"""Integration tests for Knowledge Base endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserModel, UserRole
from app.core.security import hash_password
from uuid import uuid4


@pytest.mark.asyncio
async def test_upload_document_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful document upload"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="docuploader",
        email="uploader@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login to get access token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "docuploader",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Upload document
    doc_data = {
        "title": "Test Document",
        "content": "This is a test document about machine learning and artificial intelligence.",
        "metadata": {
            "source": "test",
            "author": "Test Author",
            "tags": ["ml", "ai"]
        }
    }
    
    response = await client.post(
        "/api/v1/knowledge/documents",
        json=doc_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Document"
    assert data["content"] == doc_data["content"]
    assert "document_id" in data
    assert "embedding_id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["metadata"]["source"] == "test"


@pytest.mark.asyncio
async def test_upload_document_unauthorized(client: AsyncClient):
    """Test document upload without authentication fails"""
    doc_data = {
        "title": "Test Document",
        "content": "This is a test document."
    }
    
    response = await client.post("/api/v1/knowledge/documents", json=doc_data)
    
    assert response.status_code == 403  # No authorization header


@pytest.mark.asyncio
async def test_upload_document_viewer_forbidden(client: AsyncClient, db_session: AsyncSession):
    """Test document upload by viewer role is forbidden"""
    # Create viewer user
    user = UserModel(
        id=str(uuid4()),
        username="docviewer",
        email="docviewer@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.VIEWER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "docviewer",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Try to upload document
    doc_data = {
        "title": "Test Document",
        "content": "This is a test document."
    }
    
    response = await client.post(
        "/api/v1/knowledge/documents",
        json=doc_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_document_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful document retrieval"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="docreader",
        email="docreader@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "docreader",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # First upload a document
    doc_data = {
        "title": "Retrievable Document",
        "content": "This document will be retrieved.",
        "metadata": {"test": "value"}
    }
    
    upload_response = await client.post(
        "/api/v1/knowledge/documents",
        json=doc_data,
        headers=headers
    )
    assert upload_response.status_code == 201
    doc_id = upload_response.json()["document_id"]
    
    # Now retrieve it
    response = await client.get(
        f"/api/v1/knowledge/documents/{doc_id}",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Retrievable Document"
    assert data["content"] == "This document will be retrieved."
    assert data["document_id"] == doc_id


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test getting non-existent document returns 404"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="notfounddoc",
        email="notfounddoc@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "notfounddoc",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Try to get non-existent document
    fake_id = uuid4()
    response = await client.get(
        f"/api/v1/knowledge/documents/{fake_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful document deletion"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="docdeleter",
        email="docdeleter@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "docdeleter",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Upload a document
    doc_data = {
        "title": "Document to Delete",
        "content": "This document will be deleted."
    }
    
    upload_response = await client.post(
        "/api/v1/knowledge/documents",
        json=doc_data,
        headers=headers
    )
    assert upload_response.status_code == 201
    doc_id = upload_response.json()["document_id"]
    
    # Delete the document
    response = await client.delete(
        f"/api/v1/knowledge/documents/{doc_id}",
        headers=headers
    )
    
    assert response.status_code == 204
    
    # Verify document is no longer accessible
    get_response = await client.get(
        f"/api/v1/knowledge/documents/{doc_id}",
        headers=headers
    )
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test deleting non-existent document returns 404"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="deletenf",
        email="deletenf@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "deletenf",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Try to delete non-existent document
    fake_id = uuid4()
    response = await client.delete(
        f"/api/v1/knowledge/documents/{fake_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_documents_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful semantic search"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="searcher",
        email="searcher@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "searcher",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Upload multiple documents
    documents = [
        {
            "title": "Machine Learning Basics",
            "content": "Machine learning is a subset of artificial intelligence that focuses on learning from data.",
            "metadata": {"category": "ml"}
        },
        {
            "title": "Deep Learning Guide",
            "content": "Deep learning uses neural networks with multiple layers to learn complex patterns.",
            "metadata": {"category": "dl"}
        },
        {
            "title": "Python Programming",
            "content": "Python is a versatile programming language used for web development and data science.",
            "metadata": {"category": "programming"}
        }
    ]
    
    for doc in documents:
        upload_response = await client.post(
            "/api/v1/knowledge/documents",
            json=doc,
            headers=headers
        )
        assert upload_response.status_code == 201
    
    # Search for machine learning related content
    search_query = {
        "query": "artificial intelligence and neural networks",
        "limit": 10,
        "filters": {},
        "min_similarity": 0.0
    }
    
    response = await client.post(
        "/api/v1/knowledge/search",
        json=search_query,
        headers=headers
    )
    
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) > 0
    
    # Verify result structure
    for result in results:
        assert "document_id" in result
        assert "title" in result
        assert "content_snippet" in result
        assert "similarity_score" in result
        assert "metadata" in result
        assert 0.0 <= result["similarity_score"] <= 1.0
    
    # Results should be ordered by similarity score (descending)
    if len(results) > 1:
        for i in range(len(results) - 1):
            assert results[i]["similarity_score"] >= results[i + 1]["similarity_score"]


@pytest.mark.asyncio
async def test_search_documents_with_filters(client: AsyncClient, db_session: AsyncSession):
    """Test semantic search with metadata filters"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="filtersearch",
        email="filtersearch@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "filtersearch",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Upload documents with different categories
    documents = [
        {
            "title": "ML Document 1",
            "content": "Machine learning content about supervised learning.",
            "metadata": {"category": "ml", "level": "beginner"}
        },
        {
            "title": "ML Document 2",
            "content": "Advanced machine learning techniques and algorithms.",
            "metadata": {"category": "ml", "level": "advanced"}
        },
        {
            "title": "DL Document",
            "content": "Deep learning with convolutional neural networks.",
            "metadata": {"category": "dl", "level": "advanced"}
        }
    ]
    
    for doc in documents:
        upload_response = await client.post(
            "/api/v1/knowledge/documents",
            json=doc,
            headers=headers
        )
        assert upload_response.status_code == 201
    
    # Search with category filter
    search_query = {
        "query": "machine learning",
        "limit": 10,
        "filters": {"category": "ml"},
        "min_similarity": 0.0
    }
    
    response = await client.post(
        "/api/v1/knowledge/search",
        json=search_query,
        headers=headers
    )
    
    assert response.status_code == 200
    results = response.json()
    
    # All results should have category "ml"
    for result in results:
        assert result["metadata"]["category"] == "ml"


@pytest.mark.asyncio
async def test_search_documents_empty_results(client: AsyncClient, db_session: AsyncSession):
    """Test search with no matching documents"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="emptysearch",
        email="emptysearch@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "emptysearch",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Search without uploading any documents
    search_query = {
        "query": "nonexistent content that should not match anything",
        "limit": 10,
        "filters": {},
        "min_similarity": 0.9  # High threshold
    }
    
    response = await client.post(
        "/api/v1/knowledge/search",
        json=search_query,
        headers=headers
    )
    
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    # May be empty or have very low similarity scores


@pytest.mark.asyncio
async def test_complete_knowledge_workflow(client: AsyncClient, db_session: AsyncSession):
    """Test complete knowledge base lifecycle: upload, search, retrieve, delete"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="kbworkflow",
        email="kbworkflow@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "kbworkflow",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. Upload document
    doc_data = {
        "title": "Workflow Test Document",
        "content": "This document tests the complete knowledge base workflow including upload, search, and deletion.",
        "metadata": {"test": "workflow"}
    }
    
    upload_response = await client.post(
        "/api/v1/knowledge/documents",
        json=doc_data,
        headers=headers
    )
    assert upload_response.status_code == 201
    doc_id = upload_response.json()["document_id"]
    
    # 2. Retrieve document
    get_response = await client.get(
        f"/api/v1/knowledge/documents/{doc_id}",
        headers=headers
    )
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Workflow Test Document"
    
    # 3. Search for document
    search_response = await client.post(
        "/api/v1/knowledge/search",
        json={
            "query": "workflow test document",
            "limit": 10,
            "filters": {},
            "min_similarity": 0.0
        },
        headers=headers
    )
    assert search_response.status_code == 200
    search_results = search_response.json()
    assert len(search_results) > 0
    assert any(r["document_id"] == doc_id for r in search_results)
    
    # 4. Delete document
    delete_response = await client.delete(
        f"/api/v1/knowledge/documents/{doc_id}",
        headers=headers
    )
    assert delete_response.status_code == 204
    
    # 5. Verify document is deleted
    get_deleted_response = await client.get(
        f"/api/v1/knowledge/documents/{doc_id}",
        headers=headers
    )
    assert get_deleted_response.status_code == 404
    
    # 6. Verify document no longer appears in search
    search_after_delete = await client.post(
        "/api/v1/knowledge/search",
        json={
            "query": "workflow test document",
            "limit": 10,
            "filters": {},
            "min_similarity": 0.0
        },
        headers=headers
    )
    assert search_after_delete.status_code == 200
    results_after_delete = search_after_delete.json()
    assert not any(r["document_id"] == doc_id for r in results_after_delete)

