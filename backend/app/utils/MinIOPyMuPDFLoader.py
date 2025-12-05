from typing import List
from io import BytesIO
from pypdf import PdfReader  # Use pypdf instead of PyMuPDF
from langchain_core.document_loaders.base import BaseLoader
from langchain_core.documents import Document
from minio import Minio

class MinIOPyMuPDFLoader(BaseLoader):
    def __init__(self, minio_client: Minio, bucket_name: str, object_name: str):
        self.minio_client = minio_client
        self.bucket_name = bucket_name
        self.object_name = object_name

    def load(self) -> List[Document]:
        response = self.minio_client.get_object(bucket_name=self.bucket_name, object_name=self.object_name)
        pdf_bytes = response.read()
        
        # Use BytesIO to create a file-like object for PdfReader
        pdf_stream = BytesIO(pdf_bytes)
        reader = PdfReader(pdf_stream)

        documents = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            metadata = {
                "source": self.object_name,
                "page": i + 1
            }
            documents.append(Document(page_content=text, metadata=metadata))
        return documents