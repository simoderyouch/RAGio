from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime 
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import json
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import JSONB
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    user_name = Column(String, index=True, unique=True)
    email = Column(String, index=True, unique=True)
    hashed_password = Column(String)
    refresh_token = Column(String, nullable=True)
    email_verified = Column(Boolean, default=False) 
    email_verification_token = Column(String, nullable=True)

    uploaded_files = relationship("UploadedFile", back_populates="owner")
    chats = relationship("Chat", back_populates="user")


    def update_refresh_token(self, refresh_token):
        self.refresh_token = refresh_token


class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, index=True)
    file_type = Column(String, index=True)
    file_path = Column(String)
    embedding_path = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))  
    file_size = Column(Integer)  
    
    # Background processing status
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    task_id = Column(String, nullable=True)  # Celery task ID
    error_message = Column(String, nullable=True)  # Error details if processing failed

    owner = relationship("User", back_populates="uploaded_files")
    chats = relationship("Chat", back_populates="uploaded_file")


   
class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String , nullable=True)
    response = Column(String , nullable=True)
    source = Column(JSONB , nullable=True)
    created_at_question = Column(DateTime, default=func.now() , nullable=True)  # Timestamp for when the question was created
    created_at_response = Column(DateTime , nullable=True)  # Timestamp for when the response was created
    user_id = Column(Integer, ForeignKey("users.id"))
    uploaded_file_id = Column(Integer, ForeignKey("uploaded_files.id"))

    user = relationship("User", back_populates="chats")
    uploaded_file = relationship("UploadedFile", back_populates="chats") 
    def set_source(self, source):
        self.source = json.dumps(source)

    def get_source(self):
        return json.loads(self.source) if self.source else []
    
    
    
