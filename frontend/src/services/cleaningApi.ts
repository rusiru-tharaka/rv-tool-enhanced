/**
 * Cleaning API Service
 * Production-grade API service for RVTool file cleaning functionality
 */

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
const CLEANING_API_BASE = `${API_BASE_URL}/api/cleaning`;

// Types
interface CleaningSession {
  session_id: string;
  original_filename: string;
  file_size: number;
  status: string;
  upload_timestamp: string;
  header_validation?: HeaderValidationResult;
  data_validation?: DataValidationResult;
  cleanup_result?: CleanupResult;
}

interface HeaderValidationResult {
  is_valid: boolean;
  missing_headers: string[];
  extra_headers: string[];
  total_columns: number;
  required_columns_found: number;
}

interface ValidationIssue {
  issue_type: string;
  severity: string;
  column: string;
  row_index: number;
  current_value: any;
  expected_value?: string;
  description: string;
  suggestion?: string;
}

interface DataValidationResult {
  total_records: number;
  valid_records: number;
  issues: ValidationIssue[];
  duplicate_groups: number[][];
}

interface CleanupSelection {
  remove_duplicates: boolean;
  remove_null_values: boolean;
  remove_zero_values: boolean;
  remove_invalid_values: boolean;
  selected_rows_to_remove: number[];
  keep_first_duplicate: boolean;
}

interface CleanupResult {
  original_record_count: number;
  cleaned_record_count: number;
  removed_record_count: number;
  removed_rows: number[];
  cleanup_summary: Record<string, number>;
}

interface ApiResponse<T> {
  success: boolean;
  message: string;
  session_id?: string;
  session?: CleaningSession;
  header_validation?: HeaderValidationResult;
  data_validation?: DataValidationResult;
  cleanup_result?: CleanupResult;
  cleaned_file_url?: string;
}

interface ApiError {
  error: string;
  details?: string;
  session_id?: string;
  success: false;
}

class CleaningApiService {
  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${CLEANING_API_BASE}${endpoint}`;
    
    const defaultOptions: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, defaultOptions);
      
      if (!response.ok) {
        let errorData: ApiError;
        try {
          errorData = await response.json();
        } catch {
          errorData = {
            error: `HTTP ${response.status}: ${response.statusText}`,
            success: false
          };
        }
        throw new Error(errorData.error || `Request failed with status ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`API request failed: ${url}`, error);
      throw error;
    }
  }

  /**
   * Upload file for cleaning
   */
  async uploadFile(file: File): Promise<ApiResponse<CleaningSession>> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${CLEANING_API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorData: ApiError;
      try {
        errorData = await response.json();
      } catch {
        errorData = {
          error: `Upload failed with status ${response.status}`,
          success: false
        };
      }
      throw new Error(errorData.error || 'Upload failed');
    }

    return response.json();
  }

  /**
   * Validate column headers
   */
  async validateHeaders(sessionId: string): Promise<ApiResponse<HeaderValidationResult>> {
    return this.makeRequest(`/validate-headers/${sessionId}`, {
      method: 'POST',
    });
  }

  /**
   * Validate data
   */
  async validateData(
    sessionId: string,
    options: {
      validate_duplicates?: boolean;
      validate_null_values?: boolean;
      validate_zero_values?: boolean;
      validate_logical_constraints?: boolean;
    } = {}
  ): Promise<ApiResponse<DataValidationResult>> {
    return this.makeRequest(`/validate-data/${sessionId}`, {
      method: 'POST',
      body: JSON.stringify({
        validate_duplicates: options.validate_duplicates ?? true,
        validate_null_values: options.validate_null_values ?? true,
        validate_zero_values: options.validate_zero_values ?? true,
        validate_logical_constraints: options.validate_logical_constraints ?? true,
      }),
    });
  }

  /**
   * Cleanup data
   */
  async cleanupData(
    sessionId: string,
    cleanupSelection: CleanupSelection
  ): Promise<ApiResponse<CleanupResult>> {
    return this.makeRequest(`/cleanup/${sessionId}`, {
      method: 'POST',
      body: JSON.stringify({
        cleanup_selection: cleanupSelection,
      }),
    });
  }

  /**
   * Get session status
   */
  async getSessionStatus(sessionId: string): Promise<ApiResponse<CleaningSession>> {
    return this.makeRequest(`/session/${sessionId}`, {
      method: 'GET',
    });
  }

  /**
   * Delete session
   */
  async deleteSession(sessionId: string): Promise<{ message: string }> {
    return this.makeRequest(`/session/${sessionId}`, {
      method: 'DELETE',
    });
  }

  /**
   * Get download URL for cleaned file
   */
  getDownloadUrl(sessionId: string): string {
    return `${CLEANING_API_BASE}/download/${sessionId}`;
  }

  /**
   * Download cleaned file
   */
  async downloadCleanedFile(sessionId: string): Promise<void> {
    const url = this.getDownloadUrl(sessionId);
    
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Download failed with status ${response.status}`);
      }

      // Get filename from response headers or use default
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'cleaned_file.xlsx';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Create blob and download
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Download failed:', error);
      throw error;
    }
  }

  /**
   * Download removed data file with cleanup reasons
   */
  async downloadRemovedData(sessionId: string): Promise<void> {
    const url = `${CLEANING_API_BASE}/download-removed/${sessionId}`;
    
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Download failed with status ${response.status}`);
      }

      // Get filename from response headers or use default
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'removed_data.xlsx';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Create blob and download
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      console.error('Download removed data failed:', error);
      throw error;
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{
    status: string;
    service: string;
    active_sessions: number;
    max_file_size_mb: number;
    supported_extensions: string[];
  }> {
    return this.makeRequest('/health', {
      method: 'GET',
    });
  }

  /**
   * Cleanup expired sessions (admin)
   */
  async cleanupExpiredSessions(): Promise<{ message: string }> {
    return this.makeRequest('/cleanup-expired', {
      method: 'POST',
    });
  }
}

// Export singleton instance
export const cleaningApiService = new CleaningApiService();

// Export types for use in components
export type {
  CleaningSession,
  HeaderValidationResult,
  DataValidationResult,
  ValidationIssue,
  CleanupSelection,
  CleanupResult,
  ApiResponse,
  ApiError
};
