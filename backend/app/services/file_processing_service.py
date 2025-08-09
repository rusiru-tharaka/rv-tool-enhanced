"""
File Processing Service for RVTools Excel files
Optimized for handling 2000+ VM datasets with progress tracking
"""
import os
import io
import logging
from typing import List, Dict, Any, Optional, Generator, Callable
import pandas as pd
from datetime import datetime
import hashlib
import json

logger = logging.getLogger(__name__)

class FileProcessingService:
    """Service for processing RVTools Excel files efficiently"""
    
    def __init__(self):
        self.chunk_size = 500  # Process VMs in chunks for better memory management
        self.supported_extensions = ['.xlsx', '.xls']
        self.required_columns = ['VM', 'CPUs', 'Memory']  # Minimum required columns
    
    def validate_file(self, filename: str, file_content: bytes) -> Dict[str, Any]:
        """
        Validate uploaded file
        
        Args:
            filename: Original filename
            file_content: File content as bytes
            
        Returns:
            Dict with validation results
        """
        try:
            # Check file extension
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in self.supported_extensions:
                return {
                    'valid': False,
                    'error': f'Unsupported file type. Supported: {", ".join(self.supported_extensions)}',
                    'error_code': 'INVALID_FILE_TYPE'
                }
            
            # Check file size (max 100MB for safety)
            max_size = 100 * 1024 * 1024  # 100MB
            if len(file_content) > max_size:
                return {
                    'valid': False,
                    'error': f'File too large. Maximum size: {max_size // (1024*1024)}MB',
                    'error_code': 'FILE_TOO_LARGE'
                }
            
            # Try to read Excel file structure
            try:
                excel_file = pd.ExcelFile(io.BytesIO(file_content))
                sheets = excel_file.sheet_names
                
                # Check for vInfo sheet (standard RVTools sheet)
                if 'vInfo' not in sheets:
                    return {
                        'valid': False,
                        'error': 'vInfo sheet not found. Please ensure this is a valid RVTools export.',
                        'error_code': 'MISSING_VINFO_SHEET',
                        'available_sheets': sheets
                    }
                
                # Validate column structure
                df_sample = pd.read_excel(io.BytesIO(file_content), sheet_name='vInfo', nrows=5)
                missing_columns = [col for col in self.required_columns if col not in df_sample.columns]
                
                if missing_columns:
                    return {
                        'valid': False,
                        'error': f'Missing required columns: {", ".join(missing_columns)}',
                        'error_code': 'MISSING_COLUMNS',
                        'available_columns': list(df_sample.columns),
                        'missing_columns': missing_columns
                    }
                
                # Get basic file info
                total_rows = len(pd.read_excel(io.BytesIO(file_content), sheet_name='vInfo'))
                
                return {
                    'valid': True,
                    'filename': filename,
                    'size_bytes': len(file_content),
                    'size_mb': round(len(file_content) / (1024 * 1024), 2),
                    'total_vms': total_rows,
                    'sheets': sheets,
                    'columns': list(df_sample.columns),
                    'file_hash': hashlib.md5(file_content).hexdigest()
                }
                
            except Exception as e:
                return {
                    'valid': False,
                    'error': f'Failed to read Excel file: {str(e)}',
                    'error_code': 'EXCEL_READ_ERROR'
                }
                
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            return {
                'valid': False,
                'error': f'File validation failed: {str(e)}',
                'error_code': 'VALIDATION_ERROR'
            }
    
    def process_file_chunked(
        self, 
        file_content: bytes, 
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Process RVTools file in chunks for memory efficiency
        
        Args:
            file_content: File content as bytes
            progress_callback: Optional callback for progress updates
            
        Yields:
            Dict with VM data chunks
        """
        try:
            # Read the full dataframe first to get total count
            df = pd.read_excel(io.BytesIO(file_content), sheet_name='vInfo')
            total_rows = len(df)
            
            logger.info(f"Processing {total_rows} VMs in chunks of {self.chunk_size}")
            
            # Process in chunks
            for chunk_start in range(0, total_rows, self.chunk_size):
                chunk_end = min(chunk_start + self.chunk_size, total_rows)
                chunk_df = df.iloc[chunk_start:chunk_end]
                
                # Convert chunk to VM inventory format
                vm_chunk = []
                for _, row in chunk_df.iterrows():
                    vm_data = self._row_to_vm_data(row)
                    if vm_data:
                        vm_chunk.append(vm_data)
                
                # Update progress
                if progress_callback:
                    progress_callback(chunk_end, total_rows, f"Processed {chunk_end}/{total_rows} VMs")
                
                yield {
                    'chunk_index': chunk_start // self.chunk_size,
                    'chunk_start': chunk_start,
                    'chunk_end': chunk_end,
                    'chunk_size': len(vm_chunk),
                    'total_rows': total_rows,
                    'vm_data': vm_chunk,
                    'progress_percentage': (chunk_end / total_rows) * 100
                }
                
        except Exception as e:
            logger.error(f"Chunked processing failed: {e}")
            raise
    
    def process_file_complete(self, file_content: bytes) -> Dict[str, Any]:
        """
        Process entire RVTools file at once (for smaller files)
        
        Args:
            file_content: File content as bytes
            
        Returns:
            Dict with all VM data and processing results
        """
        try:
            start_time = datetime.utcnow()
            
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_content), sheet_name='vInfo')
            total_rows = len(df)
            
            logger.info(f"Processing {total_rows} VMs in complete mode")
            
            # Convert all rows to VM data
            vm_inventory = []
            failed_rows = []
            
            for index, row in df.iterrows():
                try:
                    vm_data = self._row_to_vm_data(row)
                    if vm_data:
                        vm_inventory.append(vm_data)
                    else:
                        failed_rows.append(index)
                except Exception as e:
                    logger.warning(f"Failed to process row {index}: {e}")
                    failed_rows.append(index)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Calculate summary statistics
            summary_stats = self._calculate_summary_stats(vm_inventory)
            
            return {
                'success': True,
                'total_rows': total_rows,
                'processed_vms': len(vm_inventory),
                'failed_rows': len(failed_rows),
                'failed_row_indices': failed_rows,
                'processing_time_seconds': processing_time,
                'vm_inventory': vm_inventory,
                'summary_stats': summary_stats,
                'processing_mode': 'complete'
            }
            
        except Exception as e:
            logger.error(f"Complete processing failed: {e}")
            return {
                'success': False,
                'error': f'Processing failed: {str(e)}',
                'error_code': 'PROCESSING_ERROR'
            }
    
    def _row_to_vm_data(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Convert pandas row to VM data dictionary
        
        Args:
            row: Pandas series representing a VM row
            
        Returns:
            Dict with VM data or None if conversion fails
        """
        try:
            # Extract basic required fields
            vm_name = str(row.get('VM', f'VM_{row.name}')).strip()
            if not vm_name or vm_name == 'nan':
                vm_name = f'VM_{row.name}'
            
            cpus = int(row.get('CPUs', 2)) if pd.notna(row.get('CPUs')) else 2
            memory_mb = int(row.get('Memory', 4096)) if pd.notna(row.get('Memory')) else 4096
            
            # Extract optional fields with safe conversion
            vm_data = {
                'vm_name': vm_name,
                'cpus': max(1, cpus),  # Ensure at least 1 CPU
                'memory_mb': max(512, memory_mb),  # Ensure at least 512MB
                'provisioned_mb': self._safe_int_convert(row.get('Provisioned MB')),
                'in_use_mb': self._safe_int_convert(row.get('In Use MB')),
                'guest_os': self._safe_str_convert(row.get('OS')),
                'powerstate': self._safe_str_convert(row.get('Powerstate', 'poweredOn')),
                'host': self._safe_str_convert(row.get('Host')),
                'cluster': self._safe_str_convert(row.get('Cluster')),
                'datacenter': self._safe_str_convert(row.get('Datacenter')),
                'folder': self._safe_str_convert(row.get('Folder')),
                'resource_pool': self._safe_str_convert(row.get('Resource Pool')),
                'network_1': self._safe_str_convert(row.get('Network #1')),
                'dns_name': self._safe_str_convert(row.get('DNS Name')),
                'annotation': self._safe_str_convert(row.get('Annotation')),
                'template': self._safe_bool_convert(row.get('Template')),
                'tools_version': self._safe_str_convert(row.get('Tools Version')),
                'tools_status': self._safe_str_convert(row.get('Tools Status'))
            }
            
            return vm_data
            
        except Exception as e:
            logger.warning(f"Failed to convert row to VM data: {e}")
            return None
    
    def _safe_int_convert(self, value) -> Optional[int]:
        """Safely convert value to integer"""
        try:
            if pd.isna(value) or value == '' or value is None:
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_str_convert(self, value) -> Optional[str]:
        """Safely convert value to string"""
        try:
            if pd.isna(value) or value == '' or value is None:
                return None
            return str(value).strip()
        except (ValueError, TypeError):
            return None
    
    def _safe_bool_convert(self, value) -> bool:
        """Safely convert value to boolean"""
        try:
            if pd.isna(value) or value == '' or value is None:
                return False
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ['true', 'yes', '1', 'on']
            return bool(value)
        except (ValueError, TypeError):
            return False
    
    def _calculate_summary_stats(self, vm_inventory: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate summary statistics for processed VMs
        
        Args:
            vm_inventory: List of VM data dictionaries
            
        Returns:
            Dict with summary statistics
        """
        if not vm_inventory:
            return {
                'total_vms': 0,
                'total_cpus': 0,
                'total_memory_gb': 0,
                'total_storage_gb': 0,
                'os_breakdown': {},
                'cluster_breakdown': {},
                'powerstate_breakdown': {}
            }
        
        # Calculate totals
        total_cpus = sum(vm.get('cpus', 0) for vm in vm_inventory)
        total_memory_gb = sum((vm.get('memory_mb', 0) or 0) / 1024 for vm in vm_inventory)
        total_storage_gb = sum((vm.get('provisioned_mb', 0) or 0) / 1024 for vm in vm_inventory)
        
        # OS breakdown
        os_breakdown = {}
        for vm in vm_inventory:
            os = vm.get('guest_os') or 'Unknown'
            os_breakdown[os] = os_breakdown.get(os, 0) + 1
        
        # Cluster breakdown
        cluster_breakdown = {}
        for vm in vm_inventory:
            cluster = vm.get('cluster') or 'Unknown'
            cluster_breakdown[cluster] = cluster_breakdown.get(cluster, 0) + 1
        
        # Power state breakdown
        powerstate_breakdown = {}
        for vm in vm_inventory:
            state = vm.get('powerstate') or 'Unknown'
            powerstate_breakdown[state] = powerstate_breakdown.get(state, 0) + 1
        
        return {
            'total_vms': len(vm_inventory),
            'total_cpus': total_cpus,
            'total_memory_gb': round(total_memory_gb, 2),
            'total_storage_gb': round(total_storage_gb, 2),
            'os_breakdown': os_breakdown,
            'cluster_breakdown': cluster_breakdown,
            'powerstate_breakdown': powerstate_breakdown,
            'avg_cpus_per_vm': round(total_cpus / len(vm_inventory), 2),
            'avg_memory_gb_per_vm': round(total_memory_gb / len(vm_inventory), 2)
        }
    
    def get_processing_recommendation(self, file_size_mb: float, total_vms: int) -> Dict[str, Any]:
        """
        Get processing recommendation based on file characteristics
        
        Args:
            file_size_mb: File size in MB
            total_vms: Total number of VMs
            
        Returns:
            Dict with processing recommendations
        """
        # Thresholds for processing mode selection
        large_file_threshold_mb = 10  # 10MB
        large_vm_count_threshold = 1000  # 1000 VMs
        
        if file_size_mb > large_file_threshold_mb or total_vms > large_vm_count_threshold:
            return {
                'recommended_mode': 'chunked',
                'reason': f'Large dataset ({total_vms} VMs, {file_size_mb}MB)',
                'chunk_size': self.chunk_size,
                'estimated_chunks': (total_vms + self.chunk_size - 1) // self.chunk_size,
                'estimated_processing_time_minutes': max(1, total_vms // 500)  # Rough estimate
            }
        else:
            return {
                'recommended_mode': 'complete',
                'reason': f'Small dataset ({total_vms} VMs, {file_size_mb}MB)',
                'estimated_processing_time_seconds': max(5, total_vms // 100)  # Rough estimate
            }

# Global file processing service instance
file_processing_service = FileProcessingService()
