"""Property-based tests for Knowledge Base Service"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from uuid import uuid4, UUID
from typing import List

from app.services.knowledge_service import KnowledgeBaseService
from app.schemas.knowledge import DocumentCreate, SearchQuery


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def valid_document_create(draw):
    """Generate valid DocumentCreate instances"""
    return DocumentCreate(
        title=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' -_.,!?'
        ))),
        content=draw(st.text(min_size=1, max_size=1000, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' -_.,!?\n'
        ))),
        metadata=draw(st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(
                whitelist_categories=('Ll', 'Nd'),
                whitelist_characters='_'
            )),
            st.one_of(
                st.text(max_size=50),
                st.integers(),
                st.booleans()
            ),
            min_size=0,
            max_size=5
        ))
    )


@st.composite
def valid_search_query(draw):
    """Generate valid SearchQuery instances"""
    return SearchQuery(
        query=draw(st.text(min_size=1, max_size=200, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' -_'
        ))),
        limit=draw(st.integers(min_value=1, max_value=50)),
        filters=draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.text(max_size=50),
            min_size=0,
            max_size=3
        )),
        min_similarity=draw(st.floats(min_value=0.0, max_value=1.0))
    )


# ============================================================================
# Property Tests
# ============================================================================

# Feature: mcp-platform-backend, Property 5: Dual-Store Document Consistency
@given(doc_data=valid_document_create())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_dual_store_document_consistency(doc_data, knowledge_service_fixture):
    """
    Property 5: Dual-Store Document Consistency
    
    For any document uploaded, both MongoDB and Vector_DB should contain
    corresponding records with matching document_id.
    
    Validates: Requirements 2.1
    """
    kb_service = knowledge_service_fixture
    
    # Store document
    stored_doc = await kb_service.store_document(doc_data)
    
    # Verify document exists in MongoDB
    mongo_doc = await kb_service.get_document(stored_doc.document_id)
    assert mongo_doc is not None, "Document should exist in MongoDB"
    assert mongo_doc.document_id == stored_doc.document_id
    assert mongo_doc.title == doc_data.title
    assert mongo_doc.content == doc_data.content
    
    # Verify embedding exists in Qdrant by searching for the document
    # We search using the document's own content, which should return itself
    search_query = SearchQuery(
        query=doc_data.content[:100],  # Use first 100 chars as query
        limit=10,
        min_similarity=0.0
    )
    search_results = await kb_service.search_documents(search_query)
    
    # The document should be findable in search results
    document_ids = [result.document_id for result in search_results]
    assert stored_doc.document_id in document_ids, \
        "Document should be findable in Qdrant via semantic search"


# Feature: mcp-platform-backend, Property 6: Search Result Ordering
@given(
    doc_count=st.integers(min_value=2, max_value=10),
    query_text=st.text(min_size=1, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters=' '
    ))
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_search_result_ordering(doc_count, query_text, knowledge_service_fixture):
    """
    Property 6: Search Result Ordering
    
    For any semantic search query, the returned results should be ordered by
    descending similarity score.
    
    Validates: Requirements 2.2
    """
    kb_service = knowledge_service_fixture
    
    # Assume query is not empty after stripping
    assume(query_text.strip() != "")
    
    # Create multiple documents with varying content
    created_docs = []
    for i in range(doc_count):
        doc_data = DocumentCreate(
            title=f"Document {i}",
            content=f"{query_text} additional content {i} " * (i + 1),
            metadata={"index": i}
        )
        doc = await kb_service.store_document(doc_data)
        created_docs.append(doc)
    
    # Perform search
    search_query = SearchQuery(
        query=query_text,
        limit=doc_count,
        min_similarity=0.0
    )
    results = await kb_service.search_documents(search_query)
    
    # If we have results, verify ordering
    if len(results) > 1:
        scores = [result.similarity_score for result in results]
        
        # Assert descending order
        assert scores == sorted(scores, reverse=True), \
            "Search results should be ordered by descending similarity score"
        
        # Assert all scores are in valid range [0, 1]
        for score in scores:
            assert 0.0 <= score <= 1.0, \
                f"Similarity score {score} should be between 0 and 1"


# Feature: mcp-platform-backend, Property 7: Document Deletion Consistency
@given(doc_data=valid_document_create())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_document_deletion_consistency(doc_data, knowledge_service_fixture):
    """
    Property 7: Document Deletion Consistency
    
    For any document, when deleted, the document should be removed from both
    MongoDB and Vector_DB.
    
    Validates: Requirements 2.4
    """
    kb_service = knowledge_service_fixture
    
    # Store document
    stored_doc = await kb_service.store_document(doc_data)
    doc_id = stored_doc.document_id
    
    # Verify document exists before deletion
    mongo_doc_before = await kb_service.get_document(doc_id)
    assert mongo_doc_before is not None, "Document should exist before deletion"
    
    # Delete document
    delete_result = await kb_service.delete_document(doc_id)
    assert delete_result is True, "Deletion should succeed"
    
    # Verify document is removed from MongoDB
    mongo_doc_after = await kb_service.get_document(doc_id)
    assert mongo_doc_after is None, "Document should not exist in MongoDB after deletion"
    
    # Verify document is not in search results (removed from Qdrant)
    # Search using the document's content
    search_query = SearchQuery(
        query=doc_data.content[:100],
        limit=10,
        min_similarity=0.0
    )
    search_results = await kb_service.search_documents(search_query)
    
    # The deleted document should not appear in search results
    document_ids = [result.document_id for result in search_results]
    assert doc_id not in document_ids, \
        "Deleted document should not appear in search results (removed from Qdrant)"


# Feature: mcp-platform-backend, Property 8: Embedding Dimension Consistency
@given(
    doc_count=st.integers(min_value=2, max_value=10)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_embedding_dimension_consistency(doc_count, knowledge_service_fixture):
    """
    Property 8: Embedding Dimension Consistency
    
    For any set of documents in the knowledge base, all embeddings should have
    the same vector dimension.
    
    Validates: Requirements 2.5
    """
    kb_service = knowledge_service_fixture
    
    # Generate multiple documents with different content
    texts = []
    for i in range(doc_count):
        text = f"This is test document number {i} with unique content " * (i + 1)
        texts.append(text)
    
    # Generate embeddings for all texts
    embeddings = await kb_service.generate_embeddings_batch(texts)
    
    # Assert all embeddings have the same dimension
    assert len(embeddings) == doc_count, "Should have one embedding per text"
    
    if len(embeddings) > 0:
        first_dimension = len(embeddings[0])
        
        for i, embedding in enumerate(embeddings):
            assert len(embedding) == first_dimension, \
                f"Embedding {i} has dimension {len(embedding)}, expected {first_dimension}"
        
        # Assert dimension matches expected (1536 for text-embedding-3-small)
        assert first_dimension == 1536, \
            f"Embeddings should have dimension 1536, got {first_dimension}"


# Additional property test: Content snippet length validation
@given(doc_data=valid_document_create())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_search_result_snippet_length(doc_data, knowledge_service_fixture):
    """
    Additional property: Search result snippets should not exceed maximum length.
    
    For any document, when returned in search results, the content snippet
    should not exceed 500 characters (plus ellipsis if truncated).
    """
    kb_service = knowledge_service_fixture
    
    # Store document
    stored_doc = await kb_service.store_document(doc_data)
    
    # Search for the document
    search_query = SearchQuery(
        query=doc_data.content[:50],
        limit=10,
        min_similarity=0.0
    )
    results = await kb_service.search_documents(search_query)
    
    # Find our document in results
    for result in results:
        if result.document_id == stored_doc.document_id:
            # Verify snippet length
            snippet_length = len(result.content_snippet)
            
            # If original content is <= 500, snippet should match
            if len(doc_data.content) <= 500:
                assert snippet_length <= 500, \
                    f"Snippet should not exceed 500 chars for short content"
            else:
                # If original content is > 500, snippet should be 503 (500 + "...")
                assert snippet_length <= 503, \
                    f"Snippet should not exceed 503 chars (500 + '...')"
            
            break


# Additional property test: Metadata filtering
@given(
    doc_count=st.integers(min_value=3, max_value=10),
    filter_key=st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Ll',),
        whitelist_characters='_'
    )),
    filter_value=st.text(min_size=1, max_size=20)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
async def test_metadata_filtering(
    doc_count,
    filter_key,
    filter_value,
    knowledge_service_fixture
):
    """
    Additional property: Metadata filtering should only return matching documents.
    
    For any search query with metadata filters, all returned results should
    match the filter criteria.
    """
    kb_service = knowledge_service_fixture
    
    # Create documents with specific metadata
    matching_docs = []
    non_matching_docs = []
    
    for i in range(doc_count):
        if i % 2 == 0:
            # Matching document
            doc_data = DocumentCreate(
                title=f"Matching Document {i}",
                content=f"Content for document {i}",
                metadata={filter_key: filter_value, "index": i}
            )
            doc = await kb_service.store_document(doc_data)
            matching_docs.append(doc)
        else:
            # Non-matching document
            doc_data = DocumentCreate(
                title=f"Non-matching Document {i}",
                content=f"Content for document {i}",
                metadata={filter_key: f"different_{i}", "index": i}
            )
            doc = await kb_service.store_document(doc_data)
            non_matching_docs.append(doc)
    
    # Search with metadata filter
    search_query = SearchQuery(
        query="Content",
        limit=doc_count,
        filters={filter_key: filter_value},
        min_similarity=0.0
    )
    results = await kb_service.search_documents(search_query)
    
    # All results should be from matching documents
    result_ids = [result.document_id for result in results]
    matching_ids = [doc.document_id for doc in matching_docs]
    non_matching_ids = [doc.document_id for doc in non_matching_docs]
    
    # Assert all results are from matching documents
    for result_id in result_ids:
        assert result_id in matching_ids, \
            "Search results should only include documents matching the filter"
        assert result_id not in non_matching_ids, \
            "Search results should not include non-matching documents"
