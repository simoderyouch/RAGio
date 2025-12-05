from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List

from app.db.database import get_db
from app.db.models import UploadedFile, User, Chat
from app.utils.file_utils import sanitize_filename
from app.utils.auth import get_current_user
from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.services.document_service import remove_document_from_collection
from app.utils.minio import initialize_minio 
from app.config import MINIO_BUCKET_NAME, MINIO_ENDPOINT, MINIO_PUBLIC_ENDPOINT
from minio.error import S3Error
import io
import json
from app.utils.parse_minio_path import parse_minio_path
from app.middleware.error_handler import FileProcessingException, ValidationException, DatabaseException
from app.middleware.error_handler import get_request_id
from app.utils.logger import log_info, log_error, log_warning
from app.utils.file_format_validator import validate_file_format

minio_client = initialize_minio()
router = APIRouter()






@router.get("/process/{file_id}")
async def process_file(
    request: Request,
    file_id: int, 
    user_id: int = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Trigger background processing for a document.
    Returns immediately with task ID for status polling.
    """
    request_id = get_request_id(request)
    
    try:
        log_info(
            "Document processing request received",
            context="document_process",
            request_id=request_id,
            file_id=file_id,
            user_id=user_id
        )
        
        uploaded_file = db.query(UploadedFile).filter(
            UploadedFile.id == file_id,
            UploadedFile.owner_id == user_id
        ).first()
        if not uploaded_file:
            log_warning(
                "File not found or unauthorized access attempt",
                context="document_process",
                request_id=request_id,
                file_id=file_id,
                user_id=user_id
            )
            raise ValidationException("File not found or access denied", {"file_id": file_id})
        
        # Check if file is already being processed
        if uploaded_file.processing_status == "processing":
            log_info(
                "File is already being processed",
                context="document_process",
                request_id=request_id,
                file_id=file_id,
                task_id=uploaded_file.task_id
            )
            return {
                "message": "File is already being processed",
                "status": "processing",
                "task_id": uploaded_file.task_id,
                "file_id": file_id,
                "status_endpoint": f"/process/status/{file_id}"
            }
        
        # Check if file is already completed
        if uploaded_file.processing_status == "completed" and uploaded_file.embedding_path:
            log_info(
                "File has already been processed",
                context="document_process",
                request_id=request_id,
                file_id=file_id
            )
            return {
                "message": "File has already been processed",
                "status": "completed",
                "file_id": file_id,
                "status_endpoint": f"/process/status/{file_id}"
            }
        
        # Validate file type
        if uploaded_file.file_type.lower() not in ALLOWED_EXTENSIONS:
            log_warning(
                "Unsupported file type for processing",
                context="document_process",
                request_id=request_id,
                file_id=file_id,
                file_type=uploaded_file.file_type
            )
            raise ValidationException("Unsupported file type", {"file_type": uploaded_file.file_type})
        
        # Validate file path
        if not uploaded_file.file_path or not uploaded_file.file_path.startswith('/minio/'):
            log_warning(
                "Invalid file path format",
                context="document_process",
                request_id=request_id,
                file_id=file_id,
                file_path=uploaded_file.file_path
            )
            raise ValidationException("Invalid file path format", {"file_path": uploaded_file.file_path})
        
        from app.tasks.document_tasks import process_document_background
        
        # Trigger the background task
        task = process_document_background.delay(file_id, user_id)
        
        # Update file with task ID and status
        uploaded_file.task_id = task.id
        uploaded_file.processing_status = "processing"
        uploaded_file.error_message = None
        db.commit()
        
        log_info(
            "Background processing task triggered",
            context="document_process",
            request_id=request_id,
            file_id=file_id,
            task_id=task.id
        )
        
        return {
            "message": "Document processing started in background",
            "status": "processing",
            "task_id": task.id,
            "file_id": file_id,
            "status_endpoint": f"/process/status/{file_id}"
        }
    
    except (ValidationException, FileProcessingException, DatabaseException):
        raise
    except Exception as e:
        log_error(
            e,
            context="document_process",
            request_id=request_id,
            file_id=file_id,
            user_id=user_id
        )
        raise DatabaseException("Failed to start document processing", {"file_id": file_id})


@router.get("/process/status/{file_id}")
async def get_processing_status(
    request: Request,
    file_id: int,
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check the processing status of a document.
    Returns current status and results if completed.
    """
    request_id = get_request_id(request)
    
    try:
        log_info(
            "Processing status check",
            context="document_status",
            request_id=request_id,
            file_id=file_id,
            user_id=user_id
        )
        
        uploaded_file = db.query(UploadedFile).filter(
            UploadedFile.id == file_id,
            UploadedFile.owner_id == user_id
        ).first()
        if not uploaded_file:

            log_warning(
                "File not found or unauthorized access attempt",
                context="document_process",
                request_id=request_id,
                file_id=file_id,
                user_id=user_id
            )
            
            raise ValidationException("File not found or access denied", {"file_id": file_id})
        

        status = uploaded_file.processing_status or "pending"
        
        response = {
            "file_id": file_id,
            "status": status,
            "file_name": uploaded_file.file_name
        }
        
        # Add task ID if available
        if uploaded_file.task_id:
            response["task_id"] = uploaded_file.task_id
            
            # Get Celery task state if task exists
            try:
                from celery.result import AsyncResult
                task_result = AsyncResult(uploaded_file.task_id)
                response["task_state"] = task_result.state
                
                #
                if task_result.info:
                    if isinstance(task_result.info, dict):
                        response["task_info"] = task_result.info
            except Exception as celery_error:
                log_warning(
                    f"Could not get Celery task state: {celery_error}",
                    context="document_status",
                    request_id=request_id,
                    task_id=uploaded_file.task_id
                )
        
        if status == "completed":
            chats = db.query(Chat).filter(
                Chat.uploaded_file_id == file_id
            ).order_by(Chat.created_at_response.desc()).limit(2).all()
            
            summary = None
            questions = None
            
            for chat in chats:
                if chat.response:
                    
                    try:
                        parsed = json.loads(chat.response)
                        if isinstance(parsed, list):
                            questions = parsed
                        else:
                            summary = chat.response
                    except (json.JSONDecodeError, TypeError):
                        # Not JSON, must be summary
                        summary = chat.response
            
            response["summary"] = summary
            response["questions"] = questions
            response["collection"] = uploaded_file.embedding_path
            
            log_info(
                "Processing completed, returning results",
                context="document_status",
                request_id=request_id,
                file_id=file_id
            )
        
        # If failed, include error message
        elif status == "failed":
            response["error"] = uploaded_file.error_message or "Processing failed"
            log_warning(
                "Processing failed",
                context="document_status",
                request_id=request_id,
                file_id=file_id,
                error=response["error"]
            )
        
        elif status == "processing":
            response["message"] = "Document is currently being processed. Please check again in a few moments."
        
        elif status == "pending":
            response["message"] = "Document processing has not been started yet."
        
        return response
    
    except ValidationException:
        raise
    except Exception as e:
        log_error(
            e,
            context="document_status",
            request_id=request_id,
            file_id=file_id,
            user_id=user_id
        )
        raise DatabaseException("Failed to get processing status", {"file_id": file_id})







@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    user_id: int = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    try:
        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        
        file_content = await file.read()
        file_size_bytes = len(file_content)
        file_size_mb = file_size_bytes / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE_MB}MB"
            )

        # Validate file format before processing
        if file_extension in ['csv', 'txt', 'md']:
            is_valid, error_msg = validate_file_format(file_content, file_extension)
            if not is_valid:
                log_warning(
                    f"File format validation failed: {error_msg}",
                    context="file_upload",
                    file_extension=file_extension,
                    filename=file.filename
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid {file_extension.upper()} file format: {error_msg}"
                )

        sanitized_filename = sanitize_filename(file.filename)
        object_name = f"{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sanitized_filename}"

        # PDF, TXT, CSV, and MD files are kept as-is (no conversion needed, already validated)

        # Upload to MinIO
        try:
            minio_client.put_object(
                bucket_name=MINIO_BUCKET_NAME,
                object_name=object_name,
                data=io.BytesIO(file_content),
                length=file_size_bytes
            )
        except S3Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload to MinIO: {str(e)}"
            )

        file_url = f"/minio/{MINIO_BUCKET_NAME}/{object_name}"

        # Save in DB
        db_file = UploadedFile(
            file_name=sanitized_filename,
            file_type=file_extension.upper(),
            file_path=file_url,
            embedding_path=None,
            owner_id=user_id,
            file_size=file_size_bytes,
            upload_date=datetime.utcnow()  
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        return {
            "message": "File uploaded successfully",
            "file": {
                "id": db_file.id,
                "name": db_file.file_name,
                "type": db_file.file_type,
                "url": file_url,
                "size": db_file.file_size,
                "upload_date": db_file.upload_date.isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )





@router.get("/files", response_model=Dict[str, List[Dict]])
def get_files_for_user(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    files_by_type = {}
    
    for file in user.uploaded_files:
        file_ext = file.file_type.lower()
        if file_ext in ALLOWED_EXTENSIONS:

            if file_ext not in files_by_type:
                files_by_type[file_ext] = []
            
            files_by_type[file_ext].append({
                'id': file.id,
                'extention': file.file_type, 
                'file_name': file.file_name, 
                'processed': (True if file.embedding_path else False),
                'processing_status': file.processing_status,
                "size": file.file_size,
                "upload_date": file.upload_date.isoformat()
            })

    return files_by_type






@router.get("/file/{file_id}")
def get_file_by_id(file_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    file = db.query(UploadedFile).filter(UploadedFile.owner_id == user_id, UploadedFile.id == file_id).first()
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    if file.file_path :
        bucket_name, object_name = parse_minio_path(file.file_path)

        try:
            url = minio_client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=timedelta(hours=1)
            )
            
            # Replace internal Docker endpoint with public endpoint for browser access
            if MINIO_ENDPOINT != MINIO_PUBLIC_ENDPOINT:
                url = url.replace(MINIO_ENDPOINT, MINIO_PUBLIC_ENDPOINT)
            
            file.file_path = url
            
        except S3Error as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate presigned URL: {str(e)}"
            )
    
    file.processed = bool(file.embedding_path)
    
    return file


@router.get("/file/{file_id}/view")
def view_file(file_id: int, db: Session = Depends(get_db)):
    """
    Stream file content directly through the backend for viewing in iframe/embed.
    No authentication required - file ID acts as the access token.
    For production, add proper token-based access control.
    """
    file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    if not file.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File path not found"
        )
    
    try:
        bucket_name, object_name = parse_minio_path(file.file_path)
        
        # Get file from MinIO
        response = minio_client.get_object(bucket_name=bucket_name, object_name=object_name)
        
        # Determine content type based on file extension
        content_type_map = {
            'PDF': 'application/pdf',
            'TXT': 'text/plain',
            'CSV': 'text/csv',
            'MD': 'text/markdown',
        }
        content_type = content_type_map.get(file.file_type, 'application/octet-stream')
        
        # Stream the file
        def iterfile():
            try:
                for chunk in response.stream(32 * 1024):  # 32KB chunks
                    yield chunk
            finally:
                response.close()
                response.release_conn()
        
        return StreamingResponse(
            iterfile(),
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{file.file_name}"',
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except S3Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve file: {str(e)}"
        )




@router.delete("/file/{file_id}")
def delete_file(file_id: int, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        file = db.query(UploadedFile).filter(
            UploadedFile.owner_id == user_id,
            UploadedFile.id == file_id
        ).first()
        
        if file is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete from MinIO if file path exists and is a MinIO path
        if file.file_path and file.file_path.startswith('/minio/'):
            bucket_name, object_name = parse_minio_path(file.file_path)
            try:
                minio_client.remove_object(bucket_name=bucket_name, object_name=object_name)
            except S3Error as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to delete file from MinIO: {str(e)}"
                )
        
        # Clean up embeddings from unified Qdrant collection
        if file.embedding_path:
            try:
                result = remove_document_from_collection(user_id=user_id, file_id=file_id)
                log_info(
                    f"Removed embeddings for file {file_id}: {result.get('deleted', 0)} points deleted",
                    context="document_delete",
                    file_id=file_id,
                    user_id=user_id,
                    result=result
                )
            except Exception as e:
                log_warning(
                    f"Failed to remove embeddings for file {file_id}: {str(e)}",
                    context="document_delete",
                    file_id=file_id,
                    user_id=user_id
                )
                # Continue with deletion even if embedding cleanup fails
        
        # Delete related messages
        db.query(Chat).filter(Chat.uploaded_file_id == file_id).delete(synchronize_session=False)
        
        # Delete the file record from database
        db.delete(file)
        db.commit()
        
        return {"message": "File deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )






