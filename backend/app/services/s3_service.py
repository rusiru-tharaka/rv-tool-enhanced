"""
S3 Service for handling file uploads and downloads
Optimized for large RVTools files (2000+ VMs)
"""
import os
import boto3
import logging
from typing import Optional, Dict, Any, BinaryIO
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime, timedelta
import hashlib
import mimetypes

logger = logging.getLogger(__name__)

class S3Service:
    """S3 service for file operations"""
    
    def __init__(self):
        self.profile_name = os.getenv('AWS_PROFILE', 'smartslot')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.uploads_bucket = 'rvtool-dev-uploads-20250715'
        self.reports_bucket = 'rvtool-dev-reports-20250715'
        
        # Initialize S3 client
        try:
            session = boto3.Session(profile_name=self.profile_name)
            self.s3_client = session.client('s3', region_name=self.region)
            self.s3_resource = session.resource('s3', region_name=self.region)
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    def upload_file(
        self, 
        file_obj: BinaryIO, 
        filename: str, 
        session_id: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload file to S3 uploads bucket
        
        Args:
            file_obj: File object to upload
            filename: Original filename
            session_id: Session ID for organization
            content_type: MIME type of the file
            
        Returns:
            Dict with upload information
        """
        try:
            # Generate S3 key
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_extension = os.path.splitext(filename)[1]
            s3_key = f"sessions/{session_id}/uploads/{timestamp}_{filename}"
            
            # Detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # Calculate file hash for integrity
            file_obj.seek(0)
            file_content = file_obj.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            file_obj.seek(0)
            
            # Upload with metadata
            extra_args = {
                'ContentType': content_type,
                'Metadata': {
                    'session-id': session_id,
                    'original-filename': filename,
                    'upload-timestamp': timestamp,
                    'file-hash': file_hash,
                    'file-size': str(len(file_content))
                }
            }
            
            # Perform upload
            self.s3_client.upload_fileobj(
                file_obj,
                self.uploads_bucket,
                s3_key,
                ExtraArgs=extra_args
            )
            
            # Generate presigned URL for download (valid for 1 hour)
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.uploads_bucket, 'Key': s3_key},
                ExpiresIn=3600
            )
            
            logger.info(f"Successfully uploaded {filename} to S3: {s3_key}")
            
            return {
                'success': True,
                'bucket': self.uploads_bucket,
                'key': s3_key,
                'filename': filename,
                'size': len(file_content),
                'content_type': content_type,
                'hash': file_hash,
                'download_url': download_url,
                'upload_timestamp': timestamp
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 upload failed: {error_code} - {e}")
            return {
                'success': False,
                'error': f"S3 upload failed: {error_code}",
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return {
                'success': False,
                'error': f"Upload failed: {str(e)}"
            }
    
    def download_file(self, s3_key: str, bucket: Optional[str] = None) -> Dict[str, Any]:
        """
        Download file from S3
        
        Args:
            s3_key: S3 object key
            bucket: Bucket name (defaults to uploads bucket)
            
        Returns:
            Dict with file content and metadata
        """
        try:
            bucket = bucket or self.uploads_bucket
            
            # Get object
            response = self.s3_client.get_object(Bucket=bucket, Key=s3_key)
            
            return {
                'success': True,
                'content': response['Body'].read(),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'metadata': response.get('Metadata', {}),
                'last_modified': response.get('LastModified'),
                'size': response.get('ContentLength', 0)
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 download failed: {error_code} - {e}")
            return {
                'success': False,
                'error': f"S3 download failed: {error_code}",
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return {
                'success': False,
                'error': f"Download failed: {str(e)}"
            }
    
    def upload_report(
        self, 
        report_content: bytes, 
        report_name: str, 
        session_id: str,
        content_type: str = 'application/pdf'
    ) -> Dict[str, Any]:
        """
        Upload generated report to S3 reports bucket
        
        Args:
            report_content: Report content as bytes
            report_name: Report filename
            session_id: Session ID
            content_type: MIME type of the report
            
        Returns:
            Dict with upload information
        """
        try:
            # Generate S3 key for report
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            s3_key = f"sessions/{session_id}/reports/{timestamp}_{report_name}"
            
            # Calculate hash
            report_hash = hashlib.md5(report_content).hexdigest()
            
            # Upload with metadata
            extra_args = {
                'ContentType': content_type,
                'Metadata': {
                    'session-id': session_id,
                    'report-name': report_name,
                    'generation-timestamp': timestamp,
                    'report-hash': report_hash,
                    'report-size': str(len(report_content))
                }
            }
            
            # Perform upload
            self.s3_client.put_object(
                Bucket=self.reports_bucket,
                Key=s3_key,
                Body=report_content,
                **extra_args
            )
            
            # Generate presigned URL for download (valid for 24 hours)
            download_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.reports_bucket, 'Key': s3_key},
                ExpiresIn=86400  # 24 hours
            )
            
            logger.info(f"Successfully uploaded report {report_name} to S3: {s3_key}")
            
            return {
                'success': True,
                'bucket': self.reports_bucket,
                'key': s3_key,
                'filename': report_name,
                'size': len(report_content),
                'content_type': content_type,
                'hash': report_hash,
                'download_url': download_url,
                'generation_timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Report upload failed: {e}")
            return {
                'success': False,
                'error': f"Report upload failed: {str(e)}"
            }
    
    def list_session_files(self, session_id: str) -> Dict[str, Any]:
        """
        List all files for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            Dict with file listings
        """
        try:
            uploads = []
            reports = []
            
            # List uploads
            upload_prefix = f"sessions/{session_id}/uploads/"
            upload_response = self.s3_client.list_objects_v2(
                Bucket=self.uploads_bucket,
                Prefix=upload_prefix
            )
            
            for obj in upload_response.get('Contents', []):
                # Get metadata
                head_response = self.s3_client.head_object(
                    Bucket=self.uploads_bucket,
                    Key=obj['Key']
                )
                
                uploads.append({
                    'key': obj['Key'],
                    'filename': head_response.get('Metadata', {}).get('original-filename', 'unknown'),
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'content_type': head_response.get('ContentType', 'unknown')
                })
            
            # List reports
            report_prefix = f"sessions/{session_id}/reports/"
            report_response = self.s3_client.list_objects_v2(
                Bucket=self.reports_bucket,
                Prefix=report_prefix
            )
            
            for obj in report_response.get('Contents', []):
                # Get metadata
                head_response = self.s3_client.head_object(
                    Bucket=self.reports_bucket,
                    Key=obj['Key']
                )
                
                reports.append({
                    'key': obj['Key'],
                    'filename': head_response.get('Metadata', {}).get('report-name', 'unknown'),
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'content_type': head_response.get('ContentType', 'unknown')
                })
            
            return {
                'success': True,
                'session_id': session_id,
                'uploads': uploads,
                'reports': reports,
                'total_uploads': len(uploads),
                'total_reports': len(reports)
            }
            
        except Exception as e:
            logger.error(f"Failed to list session files: {e}")
            return {
                'success': False,
                'error': f"Failed to list files: {str(e)}"
            }
    
    def delete_file(self, s3_key: str, bucket: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete file from S3
        
        Args:
            s3_key: S3 object key
            bucket: Bucket name
            
        Returns:
            Dict with deletion result
        """
        try:
            bucket = bucket or self.uploads_bucket
            
            self.s3_client.delete_object(Bucket=bucket, Key=s3_key)
            
            logger.info(f"Successfully deleted {s3_key} from {bucket}")
            
            return {
                'success': True,
                'message': f"File {s3_key} deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return {
                'success': False,
                'error': f"Failed to delete file: {str(e)}"
            }
    
    def get_upload_presigned_url(
        self, 
        filename: str, 
        session_id: str,
        content_type: Optional[str] = None,
        expires_in: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate presigned URL for direct upload to S3
        
        Args:
            filename: Original filename
            session_id: Session ID
            content_type: MIME type
            expires_in: URL expiration time in seconds
            
        Returns:
            Dict with presigned URL and upload information
        """
        try:
            # Generate S3 key
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            s3_key = f"sessions/{session_id}/uploads/{timestamp}_{filename}"
            
            # Detect content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(filename)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # Generate presigned URL
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.uploads_bucket,
                    'Key': s3_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            
            return {
                'success': True,
                'upload_url': presigned_url,
                'key': s3_key,
                'bucket': self.uploads_bucket,
                'content_type': content_type,
                'expires_in': expires_in
            }
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return {
                'success': False,
                'error': f"Failed to generate upload URL: {str(e)}"
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check S3 service health
        
        Returns:
            Dict with health status
        """
        try:
            # Test access to both buckets
            self.s3_client.head_bucket(Bucket=self.uploads_bucket)
            self.s3_client.head_bucket(Bucket=self.reports_bucket)
            
            return {
                'status': 'healthy',
                'uploads_bucket': self.uploads_bucket,
                'reports_bucket': self.reports_bucket,
                'region': self.region,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

# Global S3 service instance
s3_service = S3Service()
