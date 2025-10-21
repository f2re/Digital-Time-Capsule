# src/s3_utils.py
import uuid
from typing import Optional
import boto3
from botocore.client import Config
from cryptography.fernet import Fernet
from .config import (
    YANDEX_ACCESS_KEY, YANDEX_SECRET_KEY, YANDEX_BUCKET_NAME,
    YANDEX_REGION, master_cipher, logger
)

def get_s3_client():
    """Initialize and return S3 client for Yandex Object Storage"""
    try:
        return boto3.client(
            service_name='s3',
            endpoint_url='https://storage.yandexcloud.net',
            aws_access_key_id=YANDEX_ACCESS_KEY,
            aws_secret_access_key=YANDEX_SECRET_KEY,
            region_name=YANDEX_REGION,
            config=Config(signature_version='s3v4')
        )
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        return None

def encrypt_and_upload_file(file_bytes: bytes, file_extension: str) -> tuple[Optional[str], Optional[bytes]]:
    """
    Encrypt file and upload to S3
    Returns (s3_key, encrypted_file_key)
    """
    try:
        # Generate unique key for this file
        file_key = Fernet.generate_key()
        file_cipher = Fernet(file_key)

        # Encrypt file content
        encrypted_content = file_cipher.encrypt(file_bytes)

        # Generate S3 key
        s3_key = f"capsules/{uuid.uuid4()}.{file_extension}.enc"

        # Upload to S3
        s3_client = get_s3_client()
        if not s3_client:
            logger.error("S3 client not available")
            return None, None

        s3_client.put_object(
            Bucket=YANDEX_BUCKET_NAME,
            Key=s3_key,
            Body=encrypted_content
        )

        # Encrypt the file key with master key
        encrypted_file_key = master_cipher.encrypt(file_key)

        logger.info(f"File uploaded to S3: {s3_key}")
        return s3_key, encrypted_file_key

    except Exception as e:
        logger.error(f"Error in encrypt_and_upload_file: {e}")
        return None, None

def download_and_decrypt_file(s3_key: str, encrypted_file_key: bytes) -> Optional[bytes]:
    """
    Download file from S3 and decrypt
    Returns decrypted file bytes
    """
    try:
        # Decrypt the file key
        file_key = master_cipher.decrypt(encrypted_file_key)
        file_cipher = Fernet(file_key)

        # Download from S3
        s3_client = get_s3_client()
        if not s3_client:
            return None

        response = s3_client.get_object(
            Bucket=YANDEX_BUCKET_NAME,
            Key=s3_key
        )
        encrypted_content = response['Body'].read()

        # Decrypt file
        decrypted_content = file_cipher.decrypt(encrypted_content)

        logger.info(f"File downloaded and decrypted: {s3_key}")
        return decrypted_content

    except Exception as e:
        logger.error(f"Error in download_and_decrypt_file: {e}")
        return None
