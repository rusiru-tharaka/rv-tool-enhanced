"""
Background Job Processing Service
Handles async analysis tasks for large datasets (2000+ VMs)
"""
import os
import json
import logging
import boto3
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import uuid
from dataclasses import dataclass, asdict
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class JobType(str, Enum):
    """Types of background jobs"""
    MIGRATION_ANALYSIS = "migration_analysis"
    COST_ANALYSIS = "cost_analysis"
    MODERNIZATION_ANALYSIS = "modernization_analysis"
    FILE_PROCESSING = "file_processing"
    REPORT_GENERATION = "report_generation"

class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class JobProgress:
    """Job progress tracking"""
    current_step: int = 0
    total_steps: int = 1
    current_message: str = "Initializing..."
    percentage: float = 0.0
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class BackgroundJob:
    """Background job data structure"""
    job_id: str
    job_type: JobType
    session_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: JobProgress = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.progress is None:
            self.progress = JobProgress()

class JobService:
    """Service for managing background jobs"""
    
    def __init__(self):
        self.profile_name = os.getenv('AWS_PROFILE', 'smartslot')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.queue_url = "https://sqs.us-east-1.amazonaws.com/783764609930/rvtool-analysis-jobs"
        self.dlq_url = "https://sqs.us-east-1.amazonaws.com/783764609930/rvtool-analysis-jobs-dlq"
        
        # Initialize SQS client
        try:
            session = boto3.Session(profile_name=self.profile_name)
            self.sqs_client = session.client('sqs', region_name=self.region)
        except Exception as e:
            logger.error(f"Failed to initialize SQS client: {e}")
            raise
        
        # In-memory job tracking (in production, use Redis or database)
        self.jobs: Dict[str, BackgroundJob] = {}
    
    def create_job(
        self, 
        job_type: JobType, 
        session_id: str, 
        job_data: Dict[str, Any] = None
    ) -> str:
        """
        Create a new background job
        
        Args:
            job_type: Type of job to create
            session_id: Session ID
            job_data: Additional job data
            
        Returns:
            Job ID
        """
        try:
            job_id = str(uuid.uuid4())
            
            # Create job object
            job = BackgroundJob(
                job_id=job_id,
                job_type=job_type,
                session_id=session_id,
                status=JobStatus.PENDING
            )
            
            # Store job
            self.jobs[job_id] = job
            
            # Prepare message for SQS
            message_body = {
                'job_id': job_id,
                'job_type': job_type.value,
                'session_id': session_id,
                'job_data': job_data or {},
                'created_at': job.created_at.isoformat()
            }
            
            # Send to SQS
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body),
                MessageAttributes={
                    'JobType': {
                        'StringValue': job_type.value,
                        'DataType': 'String'
                    },
                    'SessionId': {
                        'StringValue': session_id,
                        'DataType': 'String'
                    }
                }
            )
            
            # Update job status
            job.status = JobStatus.QUEUED
            
            logger.info(f"Created job {job_id} of type {job_type.value} for session {session_id}")
            
            return job_id
            
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise
    
    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """
        Get job by ID
        
        Args:
            job_id: Job ID
            
        Returns:
            BackgroundJob or None
        """
        return self.jobs.get(job_id)
    
    def get_session_jobs(self, session_id: str) -> List[BackgroundJob]:
        """
        Get all jobs for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            List of BackgroundJob objects
        """
        return [job for job in self.jobs.values() if job.session_id == session_id]
    
    def update_job_progress(
        self, 
        job_id: str, 
        current_step: int, 
        total_steps: int, 
        message: str,
        details: Dict[str, Any] = None
    ) -> bool:
        """
        Update job progress
        
        Args:
            job_id: Job ID
            current_step: Current step number
            total_steps: Total number of steps
            message: Progress message
            details: Additional progress details
            
        Returns:
            True if updated successfully
        """
        try:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            # Update progress
            job.progress.current_step = current_step
            job.progress.total_steps = total_steps
            job.progress.current_message = message
            job.progress.percentage = (current_step / total_steps) * 100
            if details:
                job.progress.details.update(details)
            
            # Update status if processing
            if job.status == JobStatus.QUEUED:
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.utcnow()
            
            logger.info(f"Updated progress for job {job_id}: {job.progress.percentage:.1f}% - {message}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job progress: {e}")
            return False
    
    def complete_job(self, job_id: str, result: Dict[str, Any]) -> bool:
        """
        Mark job as completed
        
        Args:
            job_id: Job ID
            result: Job result data
            
        Returns:
            True if completed successfully
        """
        try:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.result = result
            job.progress.percentage = 100.0
            job.progress.current_message = "Completed successfully"
            
            logger.info(f"Job {job_id} completed successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete job: {e}")
            return False
    
    def fail_job(self, job_id: str, error: str) -> bool:
        """
        Mark job as failed
        
        Args:
            job_id: Job ID
            error: Error message
            
        Returns:
            True if failed successfully
        """
        try:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error = error
            job.progress.current_message = f"Failed: {error}"
            
            logger.error(f"Job {job_id} failed: {error}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fail job: {e}")
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job
        
        Args:
            job_id: Job ID
            
        Returns:
            True if cancelled successfully
        """
        try:
            job = self.jobs.get(job_id)
            if not job:
                return False
            
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                return False  # Cannot cancel completed or failed jobs
            
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            job.progress.current_message = "Cancelled by user"
            
            logger.info(f"Job {job_id} cancelled")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel job: {e}")
            return False
    
    def process_queue_messages(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Process messages from SQS queue
        
        Args:
            max_messages: Maximum number of messages to process
            
        Returns:
            List of processed messages
        """
        try:
            # Receive messages from queue
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=5,  # Long polling
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            processed_messages = []
            
            for message in messages:
                try:
                    # Parse message body
                    message_body = json.loads(message['Body'])
                    job_id = message_body['job_id']
                    
                    # Process the job (this would typically be done by a worker)
                    self._simulate_job_processing(job_id, message_body)
                    
                    # Delete message from queue after successful processing
                    self.sqs_client.delete_message(
                        QueueUrl=self.queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    
                    processed_messages.append({
                        'job_id': job_id,
                        'status': 'processed',
                        'message_id': message['MessageId']
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")
                    processed_messages.append({
                        'job_id': message_body.get('job_id', 'unknown'),
                        'status': 'failed',
                        'error': str(e),
                        'message_id': message['MessageId']
                    })
            
            return processed_messages
            
        except Exception as e:
            logger.error(f"Failed to process queue messages: {e}")
            return []
    
    def _simulate_job_processing(self, job_id: str, job_data: Dict[str, Any]):
        """
        Simulate job processing (in production, this would be actual analysis)
        
        Args:
            job_id: Job ID
            job_data: Job data from SQS message
        """
        try:
            job_type = JobType(job_data['job_type'])
            session_id = job_data['session_id']
            
            # Simulate processing steps
            steps = {
                JobType.MIGRATION_ANALYSIS: [
                    "Analyzing VM configurations",
                    "Identifying migration blockers",
                    "Calculating complexity scores",
                    "Generating recommendations"
                ],
                JobType.COST_ANALYSIS: [
                    "Mapping VMs to AWS instances",
                    "Calculating compute costs",
                    "Estimating storage costs",
                    "Generating cost summary"
                ],
                JobType.MODERNIZATION_ANALYSIS: [
                    "Analyzing workload patterns",
                    "Identifying modernization opportunities",
                    "Calculating savings potential",
                    "Prioritizing recommendations"
                ]
            }
            
            job_steps = steps.get(job_type, ["Processing job"])
            
            # Simulate processing with progress updates
            import time
            for i, step in enumerate(job_steps):
                self.update_job_progress(job_id, i + 1, len(job_steps), step)
                time.sleep(1)  # Simulate processing time
            
            # Complete the job with mock result
            result = {
                'job_type': job_type.value,
                'session_id': session_id,
                'processed_at': datetime.utcnow().isoformat(),
                'result_summary': f"Successfully completed {job_type.value} for session {session_id}"
            }
            
            self.complete_job(job_id, result)
            
        except Exception as e:
            self.fail_job(job_id, str(e))
    
    def get_job_statistics(self) -> Dict[str, Any]:
        """
        Get job processing statistics
        
        Returns:
            Dict with job statistics
        """
        try:
            total_jobs = len(self.jobs)
            status_counts = {}
            type_counts = {}
            
            for job in self.jobs.values():
                # Count by status
                status = job.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
                
                # Count by type
                job_type = job.job_type.value
                type_counts[job_type] = type_counts.get(job_type, 0) + 1
            
            # Calculate average processing time for completed jobs
            completed_jobs = [job for job in self.jobs.values() if job.status == JobStatus.COMPLETED]
            avg_processing_time = 0
            if completed_jobs:
                processing_times = []
                for job in completed_jobs:
                    if job.started_at and job.completed_at:
                        processing_time = (job.completed_at - job.started_at).total_seconds()
                        processing_times.append(processing_time)
                
                if processing_times:
                    avg_processing_time = sum(processing_times) / len(processing_times)
            
            return {
                'total_jobs': total_jobs,
                'status_breakdown': status_counts,
                'type_breakdown': type_counts,
                'completed_jobs': len(completed_jobs),
                'average_processing_time_seconds': round(avg_processing_time, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get job statistics: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check job service health
        
        Returns:
            Dict with health status
        """
        try:
            # Test SQS connectivity
            self.sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=['ApproximateNumberOfMessages']
            )
            
            return {
                'status': 'healthy',
                'queue_url': self.queue_url,
                'active_jobs': len([job for job in self.jobs.values() if job.status == JobStatus.PROCESSING]),
                'total_jobs': len(self.jobs),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

# Global job service instance
job_service = JobService()
