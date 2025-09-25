import boto3
import os
import logging
from fastapi import UploadFile, HTTPException, status
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from typing import Tuple

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

textract_client = boto3.client(
    "textract",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def upload_file_to_s3(file: UploadFile, company_id: str, object_name: str) -> str:
    """
    Uploads a file to an S3 bucket and returns its public URL.
    """
    if not S3_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="S3 bucket name is not configured.")

    try:
        file.file.seek(0)
        s3_client.upload_fileobj(
            file.file,
            S3_BUCKET_NAME,
            object_name,
            ExtraArgs={'ContentType': file.content_type}
        )
        file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{object_name}"
        logger.info(f"File {file.filename} uploaded to {file_url}")
        return file_url
    except ClientError as e:
        logger.error(f"S3 Upload Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not upload file to storage.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during S3 upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


def start_document_text_detection(object_name: str) -> str:
    """
    Starts an asynchronous text detection job in AWS Textract for a document in S3.
    Returns the JobId to track the process.
    """
    try:
        response = textract_client.start_document_text_detection(
            DocumentLocation={'S3Object': {'Bucket': S3_BUCKET_NAME, 'Name': object_name}}
        )
        job_id = response['JobId']
        logger.info(f"Started Textract job with ID: {job_id} for document {object_name}")
        return job_id
    except ClientError as e:
        logger.error(f"Textract Start Job Error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start document analysis.")

def get_document_text_detection_results(job_id: str) -> Tuple[str, list[str]]:
    """
    Polls Textract for the results of a text detection job.
    Handles pagination to retrieve all results.
    Returns the job status and a list of detected text lines.
    """
    try:
        response = textract_client.get_document_text_detection(JobId=job_id)
        status = response['JobStatus']
        
        if status == 'SUCCEEDED':
            all_lines = []
            pages = [response]
            while 'NextToken' in response:
                response = textract_client.get_document_text_detection(JobId=job_id, NextToken=response['NextToken'])
                pages.append(response)

            for page in pages:
                for block in page.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        all_lines.append(block['Text'])
            
            logger.info(f"Textract job {job_id} succeeded. Extracted {len(all_lines)} lines.")
            return 'SUCCEEDED', all_lines

        elif status == 'IN_PROGRESS':
            logger.info(f"Textract job {job_id} is still in progress.")
            return 'IN_PROGRESS', []
            
        else:
            logger.error(f"Textract job {job_id} failed with status: {status}")
            return 'FAILED', []

    except textract_client.exceptions.InvalidJobIdException:
        raise HTTPException(status_code=404, detail="Textract job not found.")
    except ClientError as e:
        logger.error(f"Textract Get Results Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document analysis results.")

