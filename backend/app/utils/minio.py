from minio import Minio
from minio.error import S3Error
import io
import json
from app.config import (
    MINIO_ENDPOINT, 
    MINIO_ACCESS_KEY, 
    MINIO_SECRET_KEY, 
    MINIO_SECURE, 
    MINIO_BUCKET_NAME
)

def initialize_minio():
    """
    Initialize MinIO client and create bucket if it doesn't exist.
    Returns the MinIO client instance.
    """
    try:
        minio_client = Minio(
            endpoint=MINIO_ENDPOINT,  # MinIO server address (keyword argument)
            access_key=MINIO_ACCESS_KEY,  # Access key from config
            secret_key=MINIO_SECRET_KEY,  # Secret key from config
            secure=MINIO_SECURE  # Secure connection from config
        )

      

        if not minio_client.bucket_exists(bucket_name=MINIO_BUCKET_NAME):
            minio_client.make_bucket(bucket_name=MINIO_BUCKET_NAME)
            # Set bucket policy to allow public read access if needed
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:*",
                        "Resource": [
                            f"arn:aws:s3:::{MINIO_BUCKET_NAME}",
                            f"arn:aws:s3:::{MINIO_BUCKET_NAME}/*"
                        ]
                        
                    }
                ]
            }
            minio_client.set_bucket_policy(bucket_name=MINIO_BUCKET_NAME, policy=json.dumps(policy))

        return minio_client

    except Exception as e:
        print(f"Error initializing MinIO: {e}")
        raise
