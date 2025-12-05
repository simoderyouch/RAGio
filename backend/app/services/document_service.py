import warnings
import time
warnings.filterwarnings(
    "ignore", message="langchain is deprecated.", category=DeprecationWarning
)
import os
from typing import List, Optional
from uuid import uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.http import models
from qdrant_client.http.models import Filter, FieldCondition, MatchAny, MatchValue

from app.config import tokenizer, encoder, qdrant_client
from app.utils.logger import log_info, log_error, log_warning, log_performance
from app.middleware.error_handler import FileProcessingException
from app.services.sparse_encoder import get_sparse_encoder
from app.utils.filename_utils import normalize_filename, sanitize_for_metadata

import numpy as np


# =============================================================================
#  COLLECTION ARCHITECTURE
# =============================================================================

def get_user_collection_name(user_id: int) -> str:

    return f"user_{user_id}_knowledge"


def check_collection_has_sparse(collection_name: str) -> bool:
    """Check if a collection has sparse vector support."""
    try:
        collection_info = qdrant_client.get_collection(collection_name)

        if hasattr(collection_info.config, 'params') and collection_info.config.params:
            sparse_config = getattr(collection_info.config.params, 'sparse_vectors', None)
            if sparse_config:

                if hasattr(sparse_config, '__contains__'):
                    return 'sparse' in sparse_config
                if hasattr(sparse_config, 'keys'):
                    return 'sparse' in sparse_config.keys()
                try:
                    if isinstance(dict(sparse_config), dict):
                        return 'sparse' in dict(sparse_config)
                except:
                    pass
                return bool(sparse_config)
        return False
    except Exception as e:
        log_warning(f"Error checking sparse vectors: {e}", context="qdrant_check")
        return False


def check_collection_has_named_vectors(collection_name: str) -> bool:
    """Check if a collection uses named vectors (dense)."""
    try:
        collection_info = qdrant_client.get_collection(collection_name)
        vectors_config = None
        
        if hasattr(collection_info.config, 'params') and collection_info.config.params:
            vectors_config = getattr(collection_info.config.params, 'vectors', None)
        
        if vectors_config is None:
            log_warning(
                f"Could not determine vector config for {collection_name}",
                context="qdrant_check"
            )
            return False
        

        if hasattr(vectors_config, '__contains__'):
            return 'dense' in vectors_config
        
        if hasattr(vectors_config, 'keys'):
            return 'dense' in vectors_config.keys()
        
        if hasattr(vectors_config, 'dense'):
            return True
        
        try:
            config_dict = dict(vectors_config) if hasattr(vectors_config, '__iter__') else None
            if config_dict and 'dense' in config_dict:
                return True
        except:
            pass
        
    
        type_name = type(vectors_config).__name__
        if type_name != 'VectorParams':
            log_info(
                f"Vector config type: {type_name}, assuming named vectors",
                context="qdrant_check"
            )
            return True
        
        return False
        
    except Exception as e:
        log_warning(f"Error checking named vectors: {e}", context="qdrant_check")
        return False


def ensure_user_collection_exists(user_id: int, vector_dim: int = 1024, with_sparse: bool = True) -> tuple:
    """
    Ensure the user's unified collection exists, create if not.
    Supports both dense and sparse vectors for hybrid retrieval.
    
    Args:
        user_id: The user's ID
        vector_dim: Dimension of the embedding vectors
        with_sparse: Whether to create sparse vector support (BM25)
        
    Returns:
        Tuple of (collection_name, has_sparse, has_named_vectors)
    """
    collection_name = get_user_collection_name(user_id)
    
    try:
        # Check if collection exists
        collections = qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if collection_name not in collection_names:
            log_info(
                f"Creating unified collection for user {user_id}",
                context="qdrant_collection",
                collection_name=collection_name,
                vector_dim=vector_dim,
                with_sparse=with_sparse
            )
            
            if with_sparse:
                qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=vector_dim,
                            distance=models.Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        "sparse": models.SparseVectorParams()
                    }
                )
                has_sparse = True
                has_named_vectors = True
            else:
                # Standard dense-only configuration
                qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_dim,
                        distance=models.Distance.COSINE
                    )
                )
                has_sparse = False
                has_named_vectors = False
            
            log_info(
                f"Unified collection '{collection_name}' created successfully",
                context="qdrant_collection",
                user_id=user_id,
                with_sparse=with_sparse
            )
        else:

            has_sparse = check_collection_has_sparse(collection_name)
            has_named_vectors = check_collection_has_named_vectors(collection_name)
            
            log_info(
                f"Unified collection '{collection_name}' already exists",
                context="qdrant_collection",
                user_id=user_id,
                has_sparse=has_sparse,
                has_named_vectors=has_named_vectors
            )
            
    except Exception as e:
        log_error(
            e,
            context="qdrant_collection",
            collection_name=collection_name,
            user_id=user_id
        )
        raise
        
    return collection_name, has_sparse, has_named_vectors


def remove_document_from_collection(user_id: int, file_id: int) -> dict:
    """
    Remove all embeddings for a specific document from the user's unified collection.
    
    This is called when a document is deleted to clean up its embeddings.
    
    Args:
        user_id: The user's ID
        file_id: The file ID to remove
        
    Returns:
        dict with deletion results
    """
    start_time = time.time()
    collection_name = get_user_collection_name(user_id)
    
    try:
        log_info(
            f"Removing document embeddings from unified collection",
            context="document_deletion",
            user_id=user_id,
            file_id=file_id,
            collection_name=collection_name
        )
        
        collections = qdrant_client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if collection_name not in collection_names:
            log_warning(
                f"Collection {collection_name} does not exist, nothing to delete",
                context="document_deletion",
                user_id=user_id,
                file_id=file_id
            )
            return {"deleted": 0, "collection": collection_name, "status": "collection_not_found"}
        
        count_before = qdrant_client.count(
            collection_name=collection_name,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="file_id",
                        match=MatchValue(value=file_id)
                    )
                ]
            )
        ).count
        
        if count_before == 0:
            log_info(
                f"No embeddings found for file {file_id}",
                context="document_deletion",
                user_id=user_id,
                file_id=file_id
            )
            return {"deleted": 0, "collection": collection_name, "status": "no_points_found"}
        
        qdrant_client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="file_id",
                            match=MatchValue(value=file_id)
                        )
                    ]
                )
            )
        )
        
        duration = time.time() - start_time
        log_performance(
            "Document embeddings removed from unified collection",
            duration,
            collection_name=collection_name,
            user_id=user_id,
            file_id=file_id,
            points_deleted=count_before
        )
        
        return {
            "deleted": count_before,
            "collection": collection_name,
            "status": "success",
            "duration": f"{duration:.2f}s"
        }
        
    except Exception as e:
        duration = time.time() - start_time
        log_error(
            e,
            context="document_deletion",
            user_id=user_id,
            file_id=file_id,
            collection_name=collection_name,
            duration=duration
        )
        raise FileProcessingException(
            f"Failed to remove document embeddings: {str(e)}",
            {"user_id": user_id, "file_id": file_id}
        )




async def get_document(documents):
    start_time = time.time()
    
    if tokenizer is not None:
        text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
            tokenizer=tokenizer,
            chunk_size=1000,      
            chunk_overlap=200,    
            strip_whitespace=True,
            separators=["\n\n", "\n", ". ", " ", ""]  
        )
    else:
        log_warning(
            "Tokenizer not available, using character-based text splitter",
            context="document_chunking"
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,      
            chunk_overlap=200,    
            strip_whitespace=True,
            separators=["\n\n", "\n", ". ", " ", ""]  
        )
    
    try:
        docs = text_splitter.split_documents(documents)
        total_content = sum(len(doc.page_content.strip()) for doc in docs)
        
        if total_content == 0:
            log_warning(
                "No text content extracted from documents",
                context="document_chunking",
                num_documents=len(documents)
            )
        
        log_info(
            f"Document chunking completed",
            context="document_chunking",
            total_content=total_content,
            num_chunks=len(docs)
        )
        
        duration = time.time() - start_time
        log_performance(
            "Document chunking completed",
            duration,
            num_documents=len(documents),
            num_chunks=len(docs),
            avg_chunk_size=sum(len(doc.page_content) for doc in docs) / len(docs) if docs else 0
        )
        
        return docs
        
    except Exception as e:
        duration = time.time() - start_time
        log_error(
            e,
            context="document_chunking",
            duration=duration,
            num_documents=len(documents)
        )
        raise FileProcessingException(
            f"Failed to chunk documents: {str(e)}",
            {"num_documents": len(documents), "duration": duration}
        )


async def process_document_qdrant(
    documents, 
    user_id: int, 
    file_id: int, 
    file_name: str,
    db_path=None,  # Kept for backward compatibility, not used
    with_sparse: bool = True  # Enable sparse vectors for hybrid search
):
    """
    Process documents and add them to the user's unified Qdrant collection.
    Supports both dense and sparse (BM25) vectors for hybrid retrieval.
    
    Args:
        documents: List of LangChain Document objects
        user_id: The user's ID (used for collection name)
        file_id: The file's ID (stored in metadata for filtering)
        file_name: The file's name (stored in metadata for source attribution)
        db_path: Deprecated, kept for backward compatibility
        with_sparse: Enable sparse vector generation for BM25 search
        
    Returns:
        dict with collection name and points inserted count
    """
    start_time = time.time()
    
    try:
        # Normalize file name for consistent storage
        normalized_file_name = sanitize_for_metadata(file_name)
        
        log_info(
            "Starting document processing with unified Qdrant collection",
            context="document_processing",
            num_documents=len(documents),
            user_id=user_id,
            file_id=file_id,
            file_name=normalized_file_name,
            with_sparse=with_sparse
        )
        
        # Step 1: Chunk the documents
        docs = await get_document(documents)

        # Step 2: Extract text from each document chunk
        texts = [doc.page_content for doc in docs]

        log_info(
            f"Extracted {len(texts)} text chunks",
            context="document_processing",
            num_chunks=len(texts),
            file_id=file_id
        )

        # Step 3: Generate dense embeddings
        if encoder is None:
            raise FileProcessingException(
                "Embedding model not available - cannot process document",
                {"file_id": file_id, "user_id": user_id}
            )
        embeddings = encoder.embed_documents(texts)
        embeddings = np.array(embeddings)
        log_info(
            f"Generated dense embeddings for {len(embeddings)} chunks",
            context="document_processing",
            embedding_dim=embeddings.shape[1],
            file_id=file_id
        )
        
        # Step 4: Get unified collection name for user (check sparse support)
        collection_name, has_sparse, has_named_vectors = ensure_user_collection_exists(
            user_id, 
            vector_dim=embeddings.shape[1],
            with_sparse=with_sparse
        )
        
        # Adjust sparse usage based on collection capabilities
        use_sparse = with_sparse and has_sparse and has_named_vectors
        
        # Step 5: Generate sparse vectors for BM25 search (if collection supports it)
        sparse_vectors = None
        if use_sparse:
            sparse_encoder = get_sparse_encoder()
            sparse_vectors = sparse_encoder.encode_batch(texts, is_query=False)
            log_info(
                f"Generated sparse vectors for {len(sparse_vectors)} chunks",
                context="document_processing",
                file_id=file_id
            )
        elif with_sparse and not has_sparse:
            log_warning(
                f"Collection '{collection_name}' does not support sparse vectors. Using dense only.",
                context="document_processing",
                file_id=file_id
            )

        # Step 6: Build payloads with enhanced metadata for filtering
        payloads = []
        for idx, (text, doc) in enumerate(zip(texts, docs)):
            metadata = doc.metadata.copy()
            page_number = metadata.get("page", 0)
            source_path = metadata.get("source", "")
            
            # Get file extension
            file_ext = normalized_file_name.split('.')[-1].upper() if '.' in normalized_file_name else 'UNKNOWN'
            
            # Enhanced payload with file identification for filtering
            payload = {
                "text": text,
                "file_id": file_id,                   # Critical for filtering
                "file_name": normalized_file_name,    # Normalized for consistency
                "file_type": file_ext,                # File extension
                "chunk_id": str(uuid4()),             # Unique chunk identifier
                "page": page_number,
                "source": source_path,
                "chunk_index": idx,                   # Order within document
                "user_id": user_id,                   # User ownership
                **{k: v for k, v in metadata.items() if k not in ["text", "file_id", "file_name", "chunk_id", "page", "source", "user_id", "file_type"]}
            }
            payloads.append(payload)
        
        # Step 7: Build points with dense and optional sparse vectors
        points = []
        for idx, (dense_vector, payload) in enumerate(zip(embeddings, payloads)):
            if use_sparse and sparse_vectors and has_named_vectors:
                # Named vectors for hybrid search
                sparse_vec = sparse_vectors[idx]
                point = models.PointStruct(
                    id=str(uuid4()),
                    vector={
                        "dense": dense_vector.tolist(),
                        "sparse": models.SparseVector(
                            indices=sparse_vec.indices,
                            values=sparse_vec.values
                        ) if sparse_vec.indices else models.SparseVector(indices=[], values=[])
                    },
                    payload=payload
                )
            else:

                point = models.PointStruct(
                    id=str(uuid4()),
                    vector=dense_vector.tolist(),
                    payload=payload
                )
            points.append(point)

        # Step 8: Upsert to unified collection
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        duration = time.time() - start_time
        log_performance(
            "Document processing with unified Qdrant collection completed",
            duration,
            collection_name=collection_name,
            user_id=user_id,
            file_id=file_id,
            points_inserted=len(points),
            with_sparse=use_sparse
        )
        
        return {"collection": collection_name, "points_inserted": len(points)}
        
    except Exception as e:
        duration = time.time() - start_time
        log_error(
            e,
            context="document_processing",
            duration=duration,
            num_documents=len(documents),
            user_id=user_id,
            file_id=file_id
        )
        raise e








# =============================================================================
#  DOCUMENT RETRIEVAL WITH FILTERING
# =============================================================================

def retrieved_docs_unified(
    question: str,
    user_id: int,
    file_ids: Optional[List[int]] = None,
    exclude_file_ids: Optional[List[int]] = None,
    similarity_threshold: float = 0.2,
    max_tokens: int = 10000,
    limit: int = 30
) -> List[Document]:
    """
    Retrieve relevant documents from the user's unified collection with optional filtering.
    
    This function queries the user's unified knowledge collection and can filter by:
    - Specific file IDs (include only these files)
    - Excluded file IDs (exclude these files)
    - No filter (search across all user documents)
    
    Results are globally ranked by similarity score across all matching documents.
    
    Args:
        question: The search query
        user_id: The user's ID (determines which collection to search)
        file_ids: Optional list of file IDs to include (None = all files)
        exclude_file_ids: Optional list of file IDs to exclude
        similarity_threshold: Minimum similarity score for results
        max_tokens: Maximum tokens to retrieve (for LLM context budget)
        limit: Maximum number of chunks to retrieve
        
    Returns:
        List of Document objects with metadata including source attribution,
        or error string if retrieval fails
    """
    start_time = time.time()
    collection_name = get_user_collection_name(user_id)
    
    try:
        log_info(
            "Starting unified document retrieval",
            context="document_retrieval_unified",
            collection_name=collection_name,
            user_id=user_id,
            question_length=len(question),
            file_ids=file_ids,
            exclude_file_ids=exclude_file_ids,
            max_tokens=max_tokens
        )
        
        try:
            collections = qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            if collection_name not in collection_names:
                log_warning(
                    f"Collection {collection_name} does not exist",
                    context="document_retrieval_unified",
                    user_id=user_id
                )
                return "No documents found. Please upload and process documents first."
        except Exception as e:
            log_error(e, context="document_retrieval_unified", user_id=user_id)
            return f"Error checking collection: {str(e)}"
        
        # Build Qdrant filter based on file inclusion/exclusion
        query_filter = None
        
        if file_ids is not None and len(file_ids) > 0:
            # Include only specific files
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="file_id",
                        match=MatchAny(any=file_ids)
                    )
                ]
            )
            log_info(
                f"Filtering to {len(file_ids)} specific files",
                context="document_retrieval_unified",
                file_ids=file_ids
            )
            
        elif exclude_file_ids is not None and len(exclude_file_ids) > 0:
            # Exclude specific files
            query_filter = Filter(
                must_not=[
                    FieldCondition(
                        key="file_id",
                        match=MatchAny(any=exclude_file_ids)
                    )
                ]
            )
            log_info(
                f"Excluding {len(exclude_file_ids)} files",
                context="document_retrieval_unified",
                exclude_file_ids=exclude_file_ids
            )
        
        # Embed the question
        if encoder is None:
            log_error(
                Exception("Embedding encoder not available"),
                context="document_retrieval_unified",
                user_id=user_id
            )
            return "Embedding model not available - cannot retrieve documents"

        question_vector = encoder.embed_query(question)
        
        # Check if collection uses named vectors
        has_named_vectors = check_collection_has_named_vectors(collection_name)
        
        if has_named_vectors:
            results = qdrant_client.query_points(
                collection_name=collection_name,
                query=question_vector,
                using="dense",  
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                score_threshold=None  
            ).points
        else:
            results = qdrant_client.query_points(
                collection_name=collection_name,
                query=question_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                score_threshold=None
            ).points
        
        if not results:
            log_warning(
                "No results from unified retrieval",
                context="document_retrieval_unified",
                user_id=user_id,
                collection_name=collection_name
            )
            return "No relevant documents found."
        
        # Check if top results meet similarity threshold
        top_score = results[0].score if results else 0
        
        if top_score < similarity_threshold:
            log_info(
                f"Top similarity score ({top_score}) below threshold ({similarity_threshold})",
                context="document_retrieval_unified",
                user_id=user_id,
                top_score=top_score
            )
        
        # Convert to Document objects with token budget management
        retrieved_docs_list = []
        total_tokens = 0
        files_seen = set()
        
        for doc in results:
            if not doc.payload or not doc.payload.get("text", "").strip():
                continue
                
            text = doc.payload.get("text", "")
            estimated_tokens = len(text) // 4
            
            if total_tokens + estimated_tokens > max_tokens:
                log_info(
                    f"Token limit reached ({total_tokens}/{max_tokens}), stopping retrieval",
                    context="document_retrieval_unified",
                    user_id=user_id,
                    chunks_retrieved=len(retrieved_docs_list)
                )
                break
            
            # Extract metadata with source attribution
            file_id = doc.payload.get("file_id")
            file_name = doc.payload.get("file_name", "Unknown")
            chunk_id = doc.payload.get("chunk_id", str(doc.id) if hasattr(doc, 'id') else None)
            page = doc.payload.get("page", 0)
            score = doc.score if hasattr(doc, 'score') else None
            
            if file_id:
                files_seen.add(file_id)
            
            retrieved_docs_list.append(Document(
                page_content=text,
                metadata={
                    "file_id": file_id,
                    "file_name": file_name,
                    "chunk_id": chunk_id,
                    "page": page,
                    "score": score,
                    "source": doc.payload.get("source", ""),
                    **{k: v for k, v in doc.payload.items() 
                       if k not in ["text", "file_id", "file_name", "chunk_id", "page", "score", "source"]}
                }
            ))
            
            total_tokens += estimated_tokens
        
        # Sort by score (highest first) - already sorted by Qdrant, but ensure it
        retrieved_docs_list = sorted(
            retrieved_docs_list,
            key=lambda doc: doc.metadata.get("score", 0) or 0,
            reverse=True
        )
        
        duration = time.time() - start_time
        log_performance(
            "Unified document retrieval completed",
            duration,
            collection_name=collection_name,
            user_id=user_id,
            documents_retrieved=len(retrieved_docs_list),
            files_used=len(files_seen),
            total_tokens=total_tokens,
            top_score=top_score
        )
        
        return retrieved_docs_list
        
    except Exception as e:
        duration = time.time() - start_time
        log_error(
            e,
            context="document_retrieval_unified",
            user_id=user_id,
            collection_name=collection_name,
            duration=duration
        )
        return f"Error retrieving documents: {str(e)}"


