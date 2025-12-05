from fastapi import APIRouter, Depends, HTTPException, Body, Request, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import asc
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.db.models import Chat, UploadedFile
from app.utils.auth import get_current_user
from app.db.database import get_db
from app.services.chat_service import process_chat_request, process_general_chat
from app.middleware.error_handler import ValidationException, DatabaseException, FileProcessingException
from app.middleware.error_handler import get_request_id
from app.utils.logger import log_info, log_error, log_warning
import time

router = APIRouter()


@router.post("/general")
async def general_chat(
    request: Request,
    question: str = Body(...),
    excluded_file_ids: Optional[List[int]] = Body(default=None),
    model: str = Body(default="Mistral"),
    language: str = Body(default="Auto-detect"),
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    General chat endpoint that uses all user documents by default.
    Users can optionally exclude specific documents from the context.
    
    Args:
        question: The user's question
        excluded_file_ids: Optional list of file IDs to exclude from context
        model: The AI model to use
        language: Response language preference
    """
    request_id = get_request_id(request)
    try:
        return await process_general_chat(
            question=question,
            excluded_file_ids=excluded_file_ids or [],
            user_id=user_id,
            db=db,
            language=language,
            request_id=request_id
        )
    except (ValidationException, FileProcessingException, DatabaseException):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))







@router.post("/{file_id}")
async def chat_with_file(
    request: Request,
    question: str = Body(...), 
    document: int = Body(...), 
    model: str = Body(...), 
    language: str = Body(...),  
    file_id: int = None, 
    user_id: int = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    request_id = get_request_id(request)
    try:
        return await process_chat_request(
            question=question,
            file_id=file_id,
            user_id=user_id,
            db=db,
            language=language,
            request_id=request_id
        )
    except (ValidationException, FileProcessingException, DatabaseException):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.get("/messages/{file_id}")
async def messages_of_file(
    request: Request,
    file_id: int, 
    user_id: int = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    start_time = time.time()
    request_id = get_request_id(request)
    
    try:
        log_info(
            "Retrieving chat messages",
            context="chat_messages",
            request_id=request_id,
            file_id=file_id,
            user_id=user_id
        )
        
        file = db.query(UploadedFile).filter(UploadedFile.owner_id == user_id, UploadedFile.id == file_id).first()
        if file is None:
            log_warning(
                "File not found for message retrieval",
                context="chat_messages",
                request_id=request_id,
                file_id=file_id,
                user_id=user_id
            )
            raise ValidationException("File not found", {"file_id": file_id, "user_id": user_id})
        
        chats = db.query(Chat).filter(Chat.uploaded_file_id == file.id).order_by(asc(Chat.created_at_question)).all()
        if chats is None:
            log_warning(
                "No chats found for file",
                context="chat_messages",
                request_id=request_id,
                file_id=file_id,
                user_id=user_id
            )
            raise ValidationException("Chats not found", {"file_id": file_id, "user_id": user_id})
         
        transformed_chats = []
        for chat in chats:
            if chat.question and chat.response:
                if chat.created_at_question < chat.created_at_response:
                    transformed_chats.append({
                        "message": chat.question, 
                        "is_user_message": True, 
                        "create_at": chat.created_at_question
                    })
                    transformed_chats.append({
                        "message": chat.response, 
                        "is_user_message": False, 
                        "create_at": chat.created_at_response
                    })
                else:
                    transformed_chats.append({
                        "message": chat.response, 
                        "is_user_message": False, 
                        "create_at": chat.created_at_response
                    })
                    transformed_chats.append({
                        "message": chat.question, 
                        "is_user_message": True, 
                        "create_at": chat.created_at_question
                    })
            # If only response exists
            elif chat.response:
                transformed_chats.append({
                    "message": chat.response, 
                    "is_user_message": False, 
                    "create_at": chat.created_at_response
                })
                
        transformed_chats.sort(key=lambda x: x["create_at"])
        
        duration = time.time() - start_time
        log_info(
            f"Retrieved {len(transformed_chats)} chat messages",
            context="chat_messages",
            request_id=request_id,
            file_id=file_id,
            user_id=user_id,
            message_count=len(transformed_chats),
            duration=duration
        )
        
        return transformed_chats
        
    except (ValidationException, DatabaseException):
        raise
    except Exception as e:
        duration = time.time() - start_time
        log_error(
            e,
            context="chat_messages",
            request_id=request_id,
            file_id=file_id,
            user_id=user_id,
            duration=duration
        )
        raise DatabaseException("Failed to retrieve chat messages", {"duration": duration})

