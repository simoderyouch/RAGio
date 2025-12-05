#!/usr/bin/env python3

import os
import sys

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

def main():
    print("=" * 60)
    print("HuggingFace Model Downloader for RAG Pipeline")
    print("Lightweight Production Models")
    print("=" * 60)
    print()
    
    success_count = 0
    fail_count = 0
    
    # Download core embedding model (used for both SentenceTransformer and HuggingFaceEmbeddings)
    print("[1/4] Downloading Embedding Model (all-MiniLM-L6-v2)...")
    print("  Size: ~90MB (lightweight, production-ready)")
    try:
        from sentence_transformers import SentenceTransformer
        SentenceTransformer(EMBEDDING_MODEL)
        print(f"  ✓ {EMBEDDING_MODEL} downloaded")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        fail_count += 1
    
    print("\n[2/4] Downloading HuggingFace Embeddings (same model)...")
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL, model_kwargs={"device": "cpu"})
        print(f"  ✓ {EMBEDDING_MODEL} embeddings downloaded")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        fail_count += 1
    
    print("\n[3/4] Downloading Tokenizer...")
    try:
        from transformers import AutoTokenizer
        AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
        print(f"  ✓ {EMBEDDING_MODEL} tokenizer downloaded")
        success_count += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        fail_count += 1
    
    # Download reranker (using cross-encoder - same model, lightweight)
    print("\n[4/4] Downloading Reranker (ms-marco-MiniLM-L-6-v2)...")
    print("  Size: ~90MB (lightweight, production-ready)")
    print("  Note: This model can be used for both reranking and cross-encoder verification")
    try:
        from sentence_transformers import CrossEncoder
        CrossEncoder(RERANKER_MODEL, max_length=512, device='cpu')
        print(f"  ✓ {RERANKER_MODEL} downloaded")
        success_count += 1
        cross_encoder_downloaded = True  
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        fail_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"Successful: {success_count}")
    print(f"Failed: {fail_count}")
    
    cache_path = os.path.expanduser("~/.cache/huggingface")
    print(f"\nModels cached at: {cache_path}")
    
    # Calculate total size
    try:
        total_size = 0
        if os.path.exists(cache_path):
            for root, dirs, files in os.walk(cache_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except:
                        pass
        size_mb = total_size / (1024 * 1024)
        print(f"Total cache size: ~{size_mb:.1f} MB")
    except:
        pass
    
    if fail_count == 0:
        print("\n✓ All models downloaded successfully!")
        print("\nModel Summary:")
        print(f"  - Embedding: {EMBEDDING_MODEL} (~90MB)")
        print(f"  - Reranker & Cross-Encoder: {RERANKER_MODEL} (~90MB)")
        print("\nTotal: ~180MB (vs ~730MB with old models - 75% reduction!)")
        print("\nNote: Using the same cross-encoder model for both reranking and verification")
        print("      This is more efficient and lighter than separate models.")
        print("\nNext steps:")
        print("1. Copy the cache to your Docker container:")
        print(f"   docker cp {cache_path} <container_name>:/root/.cache/huggingface")
        print("\n2. Or mount it as a volume in docker-compose.yml:")
        print("   volumes:")
        print(f"     - {cache_path}:/root/.cache/huggingface")
        print("\n3. Update your .env file (optional - config.py has defaults):")
        print(f"   MODEL_NAME=\"{EMBEDDING_MODEL}\"")
        print(f"   EMBEDDING_MODEL=\"{EMBEDDING_MODEL}\"")
        print(f"   RERANKER_MODEL=\"{RERANKER_MODEL}\"")
        print(f"   CROSS_ENCODER_MODEL=\"{CROSS_ENCODER_MODEL}\"")
        print("\n   Note: config.py already has these as defaults, so .env is optional")
        print("\n4. Restart your backend container")
    else:
        print("\n⚠ Some models failed to download. Check your internet connection.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

