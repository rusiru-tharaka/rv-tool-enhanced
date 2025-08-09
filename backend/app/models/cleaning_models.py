"""
Data models for RVTool file cleaning functionality
Production-grade models with proper validation and type hints
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ValidationIssueType(str, Enum):
    """Types of validation issues"""
    MISSING_HEADER = "missing_header"
    DUPLICATE_RECORD = "duplicate_record"
    NULL_VALUE = "null_value"
    ZERO_VALUE = "zero_value"
    INVALID_VALUE = "invalid_value"
    LOGICAL_ERROR = "logical_error"


class ValidationIssue(BaseModel):
    """Individual validation issue"""
    issue_type: ValidationIssueType
    severity: ValidationSeverity
    column: str
    row_index: int
    current_value: Any
    expected_value: Optional[str] = None
    description: str
    suggestion: Optional[str] = None
    
    class Config:
        # Allow arbitrary types and use custom encoder for numpy types
        arbitrary_types_allowed = True
        json_encoders = {
            # Handle numpy types
            'numpy.int64': lambda v: int(v),
            'numpy.float64': lambda v: float(v),
            'numpy.bool_': lambda v: bool(v)
        }
    
    @validator('row_index', pre=True)
    def convert_row_index(cls, v):
        """Convert numpy int64 to regular int"""
        import numpy as np
        if isinstance(v, (np.integer, np.int64)):
            return int(v)
        return v
    
    @validator('current_value', pre=True)
    def convert_current_value(cls, v):
        """Convert numpy types to regular Python types"""
        import numpy as np
        if isinstance(v, (np.integer, np.int64)):
            return int(v)
        elif isinstance(v, (np.floating, np.float64)):
            return float(v)
        elif isinstance(v, np.bool_):
            return bool(v)
        elif hasattr(v, 'item'):  # numpy scalar
            return v.item()
        return v


class HeaderValidationResult(BaseModel):
    """Result of header validation"""
    is_valid: bool
    missing_headers: List[str] = []
    extra_headers: List[str] = []
    total_columns: int
    required_columns_found: int


class DataValidationResult(BaseModel):
    """Result of data validation"""
    total_records: int
    valid_records: int
    issues: List[ValidationIssue] = []
    duplicate_groups: List[List[int]] = []  # Groups of row indices with duplicates
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            'numpy.int64': lambda v: int(v),
            'numpy.float64': lambda v: float(v),
            'numpy.bool_': lambda v: bool(v)
        }
    
    @validator('duplicate_groups', pre=True)
    def convert_duplicate_groups(cls, v):
        """Convert numpy arrays to regular lists"""
        import numpy as np
        if isinstance(v, list):
            result = []
            for group in v:
                if isinstance(group, (list, np.ndarray)):
                    # Convert each item in the group to regular int
                    converted_group = []
                    for item in group:
                        if isinstance(item, (np.integer, np.int64)):
                            converted_group.append(int(item))
                        else:
                            converted_group.append(int(item))
                    result.append(converted_group)
                else:
                    result.append(group)
            return result
        return v
    
    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0
    
    @property
    def critical_issues_count(self) -> int:
        return len([i for i in self.issues if i.severity == ValidationSeverity.CRITICAL])
    
    @property
    def issues_by_type(self) -> Dict[ValidationIssueType, int]:
        result = {}
        for issue in self.issues:
            result[issue.issue_type] = result.get(issue.issue_type, 0) + 1
        return result


class CleanupSelection(BaseModel):
    """User's selection for cleanup actions"""
    remove_duplicates: bool = True
    remove_null_values: bool = True
    remove_zero_values: bool = True
    remove_invalid_values: bool = True
    selected_rows_to_remove: List[int] = []
    keep_first_duplicate: bool = True


class CleanupResult(BaseModel):
    """Result of cleanup operation"""
    original_record_count: int
    cleaned_record_count: int
    removed_record_count: int
    removed_rows: List[int] = []
    cleanup_summary: Dict[str, int] = {}
    removed_data_details: List[Dict[str, Any]] = []  # Details of removed records with reasons


class CleaningSession(BaseModel):
    """Main cleaning session model"""
    session_id: str = Field(..., description="Unique session identifier")
    original_filename: str
    file_size: int
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Validation results
    header_validation: Optional[HeaderValidationResult] = None
    data_validation: Optional[DataValidationResult] = None
    
    # Cleanup process
    cleanup_selection: Optional[CleanupSelection] = None
    cleanup_result: Optional[CleanupResult] = None
    
    # File information
    cleaned_filename: Optional[str] = None
    cleaned_file_path: Optional[str] = None
    
    # Status tracking
    status: str = "uploaded"  # uploaded, validated, cleaned, completed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['uploaded', 'validating', 'validated', 'cleaning', 'cleaned', 'completed', 'error']
        if v not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return v


class FileUploadRequest(BaseModel):
    """Request model for file upload"""
    filename: str
    file_size: int


class HeaderValidationRequest(BaseModel):
    """Request model for header validation"""
    session_id: str


class DataValidationRequest(BaseModel):
    """Request model for data validation"""
    session_id: str
    validate_duplicates: bool = True
    validate_null_values: bool = True
    validate_zero_values: bool = True
    validate_logical_constraints: bool = True


class CleanupRequest(BaseModel):
    """Request model for cleanup operation"""
    session_id: str
    cleanup_selection: CleanupSelection


class CleaningSessionResponse(BaseModel):
    """Response model for cleaning session"""
    session: CleaningSession
    message: str
    success: bool = True


class ValidationResponse(BaseModel):
    """Response model for validation operations"""
    session_id: str
    header_validation: Optional[HeaderValidationResult] = None
    data_validation: Optional[DataValidationResult] = None
    message: str
    success: bool = True


class CleanupResponse(BaseModel):
    """Response model for cleanup operations"""
    session_id: str
    cleanup_result: CleanupResult
    cleaned_file_url: Optional[str] = None
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    details: Optional[str] = None
    session_id: Optional[str] = None
    success: bool = False


# Configuration constants
class CleaningConfig:
    """Configuration constants for cleaning operations"""
    
    # Required columns for TCO calculations (UPDATED - Added Memory)
    REQUIRED_COLUMNS = [
        'VM',                                    # VM Name
        'CPUs',                                  # vCPUs  
        'Memory',                                # Memory in MiB (CRITICAL FOR TCO)
        'Powerstate',                           # Power State
        'In Use MiB',                          # Storage (Consumed) - Primary
        'Provisioned MiB',                      # Storage (Provisioned) - Fallback
        'OS according to the configuration file', # Operating System
        'Cluster',                             # VM Cluster
        'Host'                                 # VM Host
    ]
    
    # Optional but recommended columns
    RECOMMENDED_COLUMNS = [
        'Active Memory',                        # Active memory usage (for optimization)
        'Overall Cpu Readiness',               # CPU readiness percentage
        'Guest OS',                            # Alternative OS detection
        'VM Version',
        'Tools Version',
        'Tools Status',
        'Datacenter',
        'Resource Pool'
    ]
    
    # Validation rules (UPDATED - Added Memory)
    VALIDATION_RULES = {
        'CPUs': {
            'min': 1,
            'max': 128,
            'type': 'integer'
        },
        'Memory': {
            'min': 512,      # Minimum 512 MiB (0.5 GB)
            'max': 1048576,  # Maximum 1 TiB in MiB
            'type': 'numeric'
        },
        'Provisioned MiB': {
            'min': 0,
            'type': 'numeric'
        },
        'In Use MiB': {
            'min': 0,
            'type': 'numeric'
        }
    }
    
    # File constraints
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    SUPPORTED_EXTENSIONS = ['.xlsx', '.xls', '.csv']
    
    # Session settings
    SESSION_TIMEOUT_HOURS = 24
    MAX_CONCURRENT_SESSIONS = 100
