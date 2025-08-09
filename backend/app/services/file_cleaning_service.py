"""
File Cleaning Service for RVTool files
Production-grade service with comprehensive validation and cleanup capabilities
"""

import pandas as pd
import numpy as np
import uuid
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging

from ..models.cleaning_models import (
    CleaningSession, HeaderValidationResult, DataValidationResult,
    ValidationIssue, ValidationSeverity, ValidationIssueType,
    CleanupSelection, CleanupResult, CleaningConfig
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileCleaningService:
    """
    Production-grade file cleaning service for RVTool files
    Handles validation, cleanup, and file management operations
    """
    
    def __init__(self, storage_path: str = "/tmp/rvtool_cleaning"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.sessions: Dict[str, CleaningSession] = {}
        self.file_cache: Dict[str, pd.DataFrame] = {}
        
    def create_session(self, filename: str, file_content: bytes) -> CleaningSession:
        """Create a new cleaning session"""
        session_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = self.storage_path / f"{session_id}_original_{filename}"
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Create session
        session = CleaningSession(
            session_id=session_id,
            original_filename=filename,
            file_size=len(file_content),
            status="uploaded"
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created cleaning session {session_id} for file {filename}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[CleaningSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def _load_file_data(self, session_id: str) -> pd.DataFrame:
        """Load file data into DataFrame with caching"""
        if session_id in self.file_cache:
            return self.file_cache[session_id]
        
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        file_path = self.storage_path / f"{session_id}_original_{session.original_filename}"
        
        try:
            # Determine file type and load accordingly
            if session.original_filename.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                # Try to read Excel file, handle multiple sheets
                excel_file = pd.ExcelFile(file_path)
                
                # Look for vInfo sheet first (standard RVTools sheet)
                if 'vInfo' in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name='vInfo')
                else:
                    # Use first sheet if vInfo not found
                    df = pd.read_excel(file_path, sheet_name=0)
            
            # Cache the DataFrame
            self.file_cache[session_id] = df
            logger.info(f"Loaded file data for session {session_id}: {len(df)} rows, {len(df.columns)} columns")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading file for session {session_id}: {str(e)}")
            raise ValueError(f"Unable to read file: {str(e)}")
    
    def validate_headers(self, session_id: str) -> HeaderValidationResult:
        """Validate column headers against required TCO columns"""
        try:
            df = self._load_file_data(session_id)
            session = self.get_session(session_id)
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            # Get actual columns (case-insensitive comparison)
            actual_columns = [col.strip() for col in df.columns]
            actual_columns_lower = [col.lower() for col in actual_columns]
            
            # Check required columns
            required_columns = CleaningConfig.REQUIRED_COLUMNS
            required_columns_lower = [col.lower() for col in required_columns]
            
            missing_headers = []
            found_columns = 0
            
            for req_col in required_columns:
                req_col_lower = req_col.lower()
                if req_col_lower not in actual_columns_lower:
                    missing_headers.append(req_col)
                else:
                    found_columns += 1
            
            # Identify extra headers (not required but present)
            extra_headers = []
            for actual_col in actual_columns:
                if actual_col.lower() not in required_columns_lower:
                    extra_headers.append(actual_col)
            
            # Create validation result
            result = HeaderValidationResult(
                is_valid=len(missing_headers) == 0,
                missing_headers=missing_headers,
                extra_headers=extra_headers,
                total_columns=len(actual_columns),
                required_columns_found=found_columns
            )
            
            # Update session
            session.header_validation = result
            session.status = "validated" if result.is_valid else "error"
            session.updated_at = datetime.utcnow()
            
            logger.info(f"Header validation for session {session_id}: {'PASSED' if result.is_valid else 'FAILED'}")
            
            return result
            
        except Exception as e:
            logger.error(f"Header validation error for session {session_id}: {str(e)}")
            raise
    
    def validate_data(self, session_id: str, 
                     validate_duplicates: bool = True,
                     validate_null_values: bool = True,
                     validate_zero_values: bool = True,
                     validate_logical_constraints: bool = True) -> DataValidationResult:
        """Perform comprehensive data validation"""
        try:
            df = self._load_file_data(session_id)
            session = self.get_session(session_id)
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            issues = []
            duplicate_groups = []
            
            # Create column mapping (exact match for specific columns)
            column_mapping = {}
            for col in df.columns:
                col_stripped = col.strip()
                for req_col in CleaningConfig.REQUIRED_COLUMNS:
                    if col_stripped == req_col:
                        column_mapping[req_col] = col_stripped
                        break
            
            # 1. Validate duplicates using 'VM' column
            if validate_duplicates and 'VM' in column_mapping:
                vm_name_col = column_mapping['VM']
                duplicates = df[df.duplicated(subset=[vm_name_col], keep=False)]
                
                if not duplicates.empty:
                    # Group duplicates
                    for name, group in duplicates.groupby(vm_name_col):
                        duplicate_groups.append(group.index.tolist())
                        
                        for idx in group.index:
                            issues.append(ValidationIssue(
                                issue_type=ValidationIssueType.DUPLICATE_RECORD,
                                severity=ValidationSeverity.HIGH,
                                column=vm_name_col,
                                row_index=int(idx),
                                current_value=name,
                                description=f"Duplicate VM Name: {name}",
                                suggestion="Remove duplicate entries or rename VMs"
                            ))
            
            # 2. Validate null values in critical columns
            if validate_null_values:
                critical_columns = ['VM', 'CPUs', 'OS according to the configuration file']
                for col_name in critical_columns:
                    if col_name in column_mapping:
                        actual_col = column_mapping[col_name]
                        null_mask = df[actual_col].isnull()
                        
                        for idx in df[null_mask].index:
                            issues.append(ValidationIssue(
                                issue_type=ValidationIssueType.NULL_VALUE,
                                severity=ValidationSeverity.CRITICAL,
                                column=actual_col,
                                row_index=int(idx),
                                current_value=None,
                                description=f"Null value in critical column: {col_name}",
                                suggestion="Provide valid value or remove record"
                            ))
            
            # 3. Validate zero values in CPUs
            if validate_zero_values:
                zero_check_columns = ['CPUs']
                for col_name in zero_check_columns:
                    if col_name in column_mapping:
                        actual_col = column_mapping[col_name]
                        try:
                            # Convert to numeric, handling non-numeric values
                            numeric_series = pd.to_numeric(df[actual_col], errors='coerce')
                            zero_mask = (numeric_series == 0) & numeric_series.notna()
                            
                            for idx in df[zero_mask].index:
                                issues.append(ValidationIssue(
                                    issue_type=ValidationIssueType.ZERO_VALUE,
                                    severity=ValidationSeverity.HIGH,
                                    column=actual_col,
                                    row_index=int(idx),
                                    current_value=df.loc[idx, actual_col],
                                    description=f"Zero value in {col_name} (invalid for VM)",
                                    suggestion="Provide valid positive value or remove record"
                                ))
                        except Exception as e:
                            logger.warning(f"Error checking zero values in {col_name}: {str(e)}")
            
            # 4. Validate logical constraints
            if validate_logical_constraints:
                for col_name, rules in CleaningConfig.VALIDATION_RULES.items():
                    if col_name in column_mapping:
                        actual_col = column_mapping[col_name]
                        try:
                            numeric_series = pd.to_numeric(df[actual_col], errors='coerce')
                            
                            # Check minimum values
                            if 'min' in rules:
                                min_val = rules['min']
                                invalid_mask = (numeric_series < min_val) & numeric_series.notna()
                                
                                for idx in df[invalid_mask].index:
                                    issues.append(ValidationIssue(
                                        issue_type=ValidationIssueType.INVALID_VALUE,
                                        severity=ValidationSeverity.MEDIUM,
                                        column=actual_col,
                                        row_index=int(idx),
                                        current_value=df.loc[idx, actual_col],
                                        expected_value=f">= {min_val}",
                                        description=f"{col_name} value below minimum ({min_val})",
                                        suggestion=f"Value should be >= {min_val}"
                                    ))
                            
                            # Check maximum values
                            if 'max' in rules:
                                max_val = rules['max']
                                invalid_mask = (numeric_series > max_val) & numeric_series.notna()
                                
                                for idx in df[invalid_mask].index:
                                    issues.append(ValidationIssue(
                                        issue_type=ValidationIssueType.INVALID_VALUE,
                                        severity=ValidationSeverity.MEDIUM,
                                        column=actual_col,
                                        row_index=int(idx),
                                        current_value=df.loc[idx, actual_col],
                                        expected_value=f"<= {max_val}",
                                        description=f"{col_name} value above maximum ({max_val})",
                                        suggestion=f"Value should be <= {max_val}"
                                    ))
                            
                            # Check for non-numeric values where numeric expected
                            if rules.get('type') in ['integer', 'numeric']:
                                invalid_mask = numeric_series.isna() & df[actual_col].notna()
                                
                                for idx in df[invalid_mask].index:
                                    issues.append(ValidationIssue(
                                        issue_type=ValidationIssueType.INVALID_VALUE,
                                        severity=ValidationSeverity.HIGH,
                                        column=actual_col,
                                        row_index=int(idx),
                                        current_value=df.loc[idx, actual_col],
                                        expected_value="numeric value",
                                        description=f"Non-numeric value in {col_name}",
                                        suggestion="Provide valid numeric value"
                                    ))
                                    
                        except Exception as e:
                            logger.warning(f"Error validating {col_name}: {str(e)}")
            
            # Create validation result
            result = DataValidationResult(
                total_records=len(df),
                valid_records=len(df) - len(set(issue.row_index for issue in issues)),
                issues=issues,
                duplicate_groups=duplicate_groups
            )
            
            # Update session
            session.data_validation = result
            session.status = "validated"
            session.updated_at = datetime.utcnow()
            
            logger.info(f"Data validation for session {session_id}: {len(issues)} issues found")
            
            return result
            
        except Exception as e:
            logger.error(f"Data validation error for session {session_id}: {str(e)}")
            raise
    
    def cleanup_data(self, session_id: str, cleanup_selection: CleanupSelection) -> CleanupResult:
        """Perform data cleanup based on user selections"""
        try:
            df = self._load_file_data(session_id)
            session = self.get_session(session_id)
            
            if not session:
                raise ValueError(f"Session {session_id} not found")
            
            original_count = len(df)
            rows_to_remove = set()
            cleanup_summary = {}
            removed_data_details = []
            
            # Get validation results
            if not session.data_validation:
                raise ValueError("Data validation must be performed before cleanup")
            
            validation_result = session.data_validation
            
            # Track removal reasons for each row
            removal_reasons = {}  # row_index -> list of reasons
            
            # 1. Handle duplicates
            if cleanup_selection.remove_duplicates and validation_result.duplicate_groups:
                duplicate_rows = set()
                for group in validation_result.duplicate_groups:
                    if cleanup_selection.keep_first_duplicate:
                        # Keep first occurrence, remove others
                        rows_to_remove_from_group = group[1:]
                        duplicate_rows.update(rows_to_remove_from_group)
                        # Track reasons
                        for row_idx in rows_to_remove_from_group:
                            if row_idx not in removal_reasons:
                                removal_reasons[row_idx] = []
                            removal_reasons[row_idx].append("Duplicate record (keeping first occurrence)")
                    else:
                        # Remove all duplicates
                        duplicate_rows.update(group)
                        for row_idx in group:
                            if row_idx not in removal_reasons:
                                removal_reasons[row_idx] = []
                            removal_reasons[row_idx].append("Duplicate record (removing all)")
                
                rows_to_remove.update(duplicate_rows)
                cleanup_summary['duplicates_removed'] = len(duplicate_rows)
            
            # 2. Handle issues based on type
            issue_counts = {}
            for issue in validation_result.issues:
                issue_type = issue.issue_type
                row_idx = issue.row_index
                
                should_remove = False
                reason = ""
                
                if issue_type == ValidationIssueType.NULL_VALUE and cleanup_selection.remove_null_values:
                    should_remove = True
                    reason = f"Null value in {issue.column}: {issue.description}"
                elif issue_type == ValidationIssueType.ZERO_VALUE and cleanup_selection.remove_zero_values:
                    should_remove = True
                    reason = f"Zero value in {issue.column}: {issue.description}"
                elif issue_type == ValidationIssueType.INVALID_VALUE and cleanup_selection.remove_invalid_values:
                    should_remove = True
                    reason = f"Invalid value in {issue.column}: {issue.description}"
                
                if should_remove:
                    rows_to_remove.add(row_idx)
                    if row_idx not in removal_reasons:
                        removal_reasons[row_idx] = []
                    removal_reasons[row_idx].append(reason)
                    issue_counts[issue_type.value] = issue_counts.get(issue_type.value, 0) + 1
            
            # 3. Add user-selected rows
            for row_idx in cleanup_selection.selected_rows_to_remove:
                rows_to_remove.add(row_idx)
                if row_idx not in removal_reasons:
                    removal_reasons[row_idx] = []
                removal_reasons[row_idx].append("Manually selected for removal")
            
            # Create removed data details
            for row_idx in rows_to_remove:
                if row_idx < len(df):
                    row_data = df.iloc[row_idx].to_dict()
                    
                    # Convert NaN values to None for JSON serialization
                    cleaned_row_data = {}
                    for key, value in row_data.items():
                        if pd.isna(value):
                            cleaned_row_data[key] = None
                        elif isinstance(value, (np.integer, np.int64)):
                            cleaned_row_data[key] = int(value)
                        elif isinstance(value, (np.floating, np.float64)):
                            if np.isnan(value):
                                cleaned_row_data[key] = None
                            else:
                                cleaned_row_data[key] = float(value)
                        elif isinstance(value, np.bool_):
                            cleaned_row_data[key] = bool(value)
                        else:
                            cleaned_row_data[key] = str(value) if value is not None else None
                    
                    removed_data_details.append({
                        'original_row_index': int(row_idx) + 1,  # 1-based for user display
                        'removal_reasons': removal_reasons.get(row_idx, ["Unknown reason"]),
                        'data': cleaned_row_data
                    })
            
            # Perform cleanup
            cleaned_df = df.drop(index=list(rows_to_remove))
            cleaned_count = len(cleaned_df)
            
            # Save cleaned file
            cleaned_filename = f"{session_id}_cleaned_{session.original_filename}"
            cleaned_file_path = self.storage_path / cleaned_filename
            
            if session.original_filename.endswith('.csv'):
                cleaned_df.to_csv(cleaned_file_path, index=False)
            else:
                cleaned_df.to_excel(cleaned_file_path, index=False)
            
            # Save removed data file
            if removed_data_details:
                removed_filename = f"{session_id}_removed_{session.original_filename}"
                removed_file_path = self.storage_path / removed_filename
                
                # Create DataFrame for removed data
                removed_records = []
                for detail in removed_data_details:
                    record = detail['data'].copy()
                    record['Original_Row_Number'] = detail['original_row_index']
                    record['Removal_Reasons'] = '; '.join(detail['removal_reasons'])
                    removed_records.append(record)
                
                removed_df = pd.DataFrame(removed_records)
                
                if session.original_filename.endswith('.csv'):
                    removed_df.to_csv(removed_file_path, index=False)
                else:
                    removed_df.to_excel(removed_file_path, index=False)
            
            # Create cleanup result
            result = CleanupResult(
                original_record_count=original_count,
                cleaned_record_count=cleaned_count,
                removed_record_count=len(rows_to_remove),
                removed_rows=sorted(list(rows_to_remove)),
                cleanup_summary={**cleanup_summary, **issue_counts},
                removed_data_details=removed_data_details
            )
            
            # Update session
            session.cleanup_selection = cleanup_selection
            session.cleanup_result = result
            session.cleaned_filename = cleaned_filename
            session.cleaned_file_path = str(cleaned_file_path)
            session.status = "cleaned"
            session.updated_at = datetime.utcnow()
            
            # Update cache with cleaned data
            self.file_cache[f"{session_id}_cleaned"] = cleaned_df
            
            logger.info(f"Cleanup completed for session {session_id}: {original_count} -> {cleaned_count} records")
            
            return result
            
        except Exception as e:
            logger.error(f"Cleanup error for session {session_id}: {str(e)}")
            raise
    
    def get_cleaned_file_path(self, session_id: str) -> Optional[str]:
        """Get path to cleaned file"""
        session = self.get_session(session_id)
        if session and session.cleaned_file_path:
            return session.cleaned_file_path
        return None
    
    def get_removed_data_file_path(self, session_id: str) -> Optional[str]:
        """Get path to removed data file"""
        session = self.get_session(session_id)
        if session and session.original_filename:
            removed_filename = f"{session_id}_removed_{session.original_filename}"
            removed_file_path = self.storage_path / removed_filename
            if removed_file_path.exists():
                return str(removed_file_path)
        return None
    
    def cleanup_expired_sessions(self, hours: int = 24):
        """Clean up expired sessions and files"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.created_at < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            try:
                session = self.sessions[session_id]
                
                # Remove files
                original_file = self.storage_path / f"{session_id}_original_{session.original_filename}"
                if original_file.exists():
                    original_file.unlink()
                
                if session.cleaned_file_path:
                    cleaned_file = Path(session.cleaned_file_path)
                    if cleaned_file.exists():
                        cleaned_file.unlink()
                
                # Remove from cache
                self.file_cache.pop(session_id, None)
                self.file_cache.pop(f"{session_id}_cleaned", None)
                
                # Remove session
                del self.sessions[session_id]
                
                logger.info(f"Cleaned up expired session {session_id}")
                
            except Exception as e:
                logger.error(f"Error cleaning up session {session_id}: {str(e)}")


# Global service instance
file_cleaning_service = FileCleaningService()
