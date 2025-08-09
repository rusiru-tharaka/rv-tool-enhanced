import React, { useState, useCallback } from 'react';
import { Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react';

interface FileUploadSectionProps {
  onFileUpload: (file: File) => void;
  loading: boolean;
}

const FileUploadSection: React.FC<FileUploadSectionProps> = ({
  onFileUpload,
  loading
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = e.dataTransfer.files;
    if (files && files[0]) {
      handleFileSelection(files[0]);
    }
  }, []);

  const handleFileSelection = useCallback((file: File) => {
    // Validate file type
    const validExtensions = ['.xlsx', '.xls', '.csv'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    if (!validExtensions.includes(fileExtension)) {
      alert(`Invalid file type. Please select an Excel (.xlsx, .xls) or CSV (.csv) file.`);
      return;
    }

    // Validate file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      alert(`File too large. Maximum size is 50MB.`);
      return;
    }

    setSelectedFile(file);
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files[0]) {
      handleFileSelection(files[0]);
    }
  }, [handleFileSelection]);

  const handleUpload = useCallback(() => {
    if (selectedFile) {
      onFileUpload(selectedFile);
    }
  }, [selectedFile, onFileUpload]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="p-8">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Upload RVTool File for Cleaning
        </h2>
        <p className="text-gray-600">
          Upload your RVTool export file to validate and clean the data before analysis
        </p>
      </div>

      {/* File Upload Area */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${dragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
          ${loading ? 'pointer-events-none opacity-50' : ''}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          accept=".xlsx,.xls,.csv"
          onChange={handleFileInputChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={loading}
        />

        <div className="space-y-4">
          <div className="mx-auto w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
            <Upload className="w-8 h-8 text-gray-400" />
          </div>

          <div>
            <p className="text-lg font-medium text-gray-900">
              Drop your RVTool file here, or click to browse
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Supports Excel (.xlsx, .xls) and CSV (.csv) files up to 50MB
            </p>
          </div>

          {dragActive && (
            <div className="text-blue-600 font-medium">
              Drop file to upload
            </div>
          )}
        </div>
      </div>

      {/* Selected File Display */}
      {selectedFile && (
        <div className="mt-6 bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <FileText className="w-8 h-8 text-blue-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {selectedFile.name}
                </p>
                <p className="text-sm text-gray-500">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="text-sm text-green-600">Ready to upload</span>
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={handleUpload}
              disabled={loading}
              className={`
                px-6 py-2 rounded-md font-medium transition-colors
                ${loading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
                }
              `}
            >
              {loading ? 'Uploading...' : 'Upload File'}
            </button>
          </div>
        </div>
      )}

      {/* Requirements Info */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-blue-500 mt-0.5" />
          <div>
            <h3 className="text-sm font-medium text-blue-800 mb-2">
              File Requirements
            </h3>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• File must be an RVTool export (Excel or CSV format)</li>
              <li>• Required columns:</li>
              <ul className="ml-4 mt-1 space-y-1">
                <li>- <strong>VM</strong> (VM Name)</li>
                <li>- <strong>CPUs</strong> (vCPUs)</li>
                <li>- <strong>Powerstate</strong> (Power State)</li>
                <li>- <strong>In Use MiB</strong> (Storage Consumed - Primary)</li>
                <li>- <strong>Provisioned MiB</strong> (Storage Provisioned - Fallback)</li>
                <li>- <strong>OS according to the configuration file</strong> (Operating System)</li>
                <li>- <strong>Cluster</strong> (VM Cluster)</li>
                <li>- <strong>Host</strong> (VM Host)</li>
              </ul>
              <li>• Maximum file size: 50MB</li>
              <li>• For Excel files, data should be in the 'vInfo' sheet</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="mt-6 text-center">
          <div className="inline-flex items-center space-x-2 text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span>Uploading file...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUploadSection;
