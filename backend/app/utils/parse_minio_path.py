from fastapi import HTTPException

def parse_minio_path(file_path: str):
    parts = file_path.strip('/').split('/')
    if len(parts) < 4 or parts[0] != 'minio':
        raise HTTPException(status_code=400, detail="Invalid MinIO file path format")

    bucket_name = parts[1]
    object_name = '/'.join(parts[2:])
    return bucket_name, object_name
