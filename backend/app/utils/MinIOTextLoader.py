"""
MinIO Text File Loader for TXT, CSV, and MD files.
Supports loading text-based files from MinIO storage.
"""
from typing import List
from io import BytesIO
from langchain_core.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from minio import Minio


class MinIOTextLoader(BaseLoader):
    """Loader for text-based files (TXT, CSV, MD) from MinIO."""
    
    def __init__(self, minio_client: Minio, bucket_name: str, object_name: str, file_type: str = "txt"):
        """
        Initialize the text loader.
        
        Args:
            minio_client: MinIO client instance
            bucket_name: Name of the MinIO bucket
            object_name: Name of the object in MinIO
            file_type: File type ('txt', 'csv', 'md')
        """
        self.minio_client = minio_client
        self.bucket_name = bucket_name
        self.object_name = object_name
        self.file_type = file_type.lower()
    
    def load(self) -> List[Document]:
        """Load text file from MinIO and return as Document objects."""
        response = self.minio_client.get_object(
            bucket_name=self.bucket_name, 
            object_name=self.object_name
        )
        file_bytes = response.read()
        response.close()
        response.release_conn()
        
        # Decode bytes to text
        try:
            text = file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # Try Latin-1 as fallback
            try:
                text = file_bytes.decode('latin-1')
            except UnicodeDecodeError:
                # Last resort: try with error handling
                text = file_bytes.decode('utf-8', errors='ignore')
        
        # For CSV files, convert to a more readable format
        if self.file_type == 'csv':
            # Keep CSV as-is, but add metadata
            lines = text.split('\n')
            # Use first line as header if it exists
            header = lines[0] if lines else ""
            content = text
        else:
            # For TXT and MD, use content as-is
            content = text
        
        # Create a single document with metadata
        metadata = {
            "source": self.object_name,
            "file_type": self.file_type.upper(),
            "page": 1  # Text files don't have pages, but use 1 for consistency
        }
        
        return [Document(page_content=content, metadata=metadata)]

