import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Upload, 
  FileText, 
  BarChart3, 
  Zap, 
  CheckCircle, 
  Clock,
  Trash2,
  Play,
  AlertCircle,
  Settings
} from 'lucide-react';
import { useSession } from '../contexts/SessionContext';
import { apiService } from '../services/api';
import { AnalysisPhase } from '../types';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { state, createSession, loadSessions, deleteSession, clearError } = useSession();
  const [dragActive, setDragActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // Load sessions on component mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Clear error when component mounts
  useEffect(() => {
    if (state.error.hasError) {
      clearError();
    }
  }, []);

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

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileUpload(e.target.files[0]);
    }
  };

  const handleFileUpload = async (file: File) => {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xls')) {
      alert('Please upload an Excel file (.xlsx or .xls)');
      return;
    }

    setUploadedFile(file);
    setUploadProgress(0);

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      // Upload file and get VM inventory
      const uploadResult = await apiService.uploadRVToolsFile(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);

      // Create new analysis session
      const session = await createSession(uploadResult.vm_inventory);

      // Navigate to analysis page using the session ID from the created session
      if (session && session.session_id) {
        console.log('Navigating to analysis page:', session.session_id);
        navigate(`/analysis/${session.session_id}`);
      } else {
        console.error('No session ID available for navigation');
        // Fallback: try to get from state
        const sessionId = state.currentSession?.session_id;
        if (sessionId) {
          console.log('Using fallback session ID:', sessionId);
          navigate(`/analysis/${sessionId}`);
        }
      }

    } catch (error: any) {
      setUploadProgress(0);
      console.error('Upload failed:', error);
      alert('Upload failed. Please try again.');
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (window.confirm('Are you sure you want to delete this session?')) {
      await deleteSession(sessionId);
    }
  };

  const handleContinueSession = (sessionId: string) => {
    navigate(`/analysis/${sessionId}`);
  };

  const getPhaseIcon = (phase: AnalysisPhase) => {
    switch (phase) {
      case AnalysisPhase.MIGRATION_SCOPE:
        return <FileText className="h-4 w-4" />;
      case AnalysisPhase.COST_ESTIMATES:
        return <BarChart3 className="h-4 w-4" />;
      case AnalysisPhase.MODERNIZATION:
        return <Zap className="h-4 w-4" />;
      case AnalysisPhase.REPORT_GENERATION:
        return <CheckCircle className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getPhaseLabel = (phase: AnalysisPhase) => {
    switch (phase) {
      case AnalysisPhase.MIGRATION_SCOPE:
        return 'Migration Scope';
      case AnalysisPhase.COST_ESTIMATES:
        return 'Cost Estimates';
      case AnalysisPhase.MODERNIZATION:
        return 'Modernization';
      case AnalysisPhase.REPORT_GENERATION:
        return 'Reports';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Migration Analysis Dashboard</h1>
        <p className="mt-2 text-lg text-gray-600">
          Upload your RVTools export to begin comprehensive migration analysis
        </p>
      </div>

      {/* Upload Section */}
      <div className="max-w-2xl mx-auto">
        <div className="card">
          <div className="card-content">
            <div
              className={`
                relative border-2 border-dashed rounded-lg p-8 text-center transition-colors
                ${dragActive 
                  ? 'border-primary-400 bg-primary-50' 
                  : 'border-gray-300 hover:border-gray-400'
                }
              `}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <Upload className="mx-auto h-12 w-12 text-gray-400" />
              <div className="mt-4">
                <label htmlFor="file-upload" className="cursor-pointer">
                  <span className="text-lg font-medium text-gray-900">
                    Drop your RVTools file here, or{' '}
                    <span className="text-primary-600 hover:text-primary-500">browse</span>
                  </span>
                  <input
                    id="file-upload"
                    name="file-upload"
                    type="file"
                    className="sr-only"
                    accept=".xlsx,.xls"
                    onChange={handleFileInput}
                  />
                </label>
                <p className="mt-2 text-sm text-gray-500">
                  Excel files (.xlsx, .xls) up to 10MB
                </p>
              </div>

              {/* Upload Progress */}
              {uploadProgress > 0 && (
                <div className="mt-4">
                  <div className="bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="mt-2 text-sm text-gray-600">
                    {uploadProgress < 100 ? `Uploading... ${uploadProgress}%` : 'Processing complete!'}
                  </p>
                </div>
              )}

              {/* Uploaded File Info */}
              {uploadedFile && (
                <div className="mt-4 p-3 bg-green-50 rounded-md">
                  <div className="flex items-center">
                    <CheckCircle className="h-5 w-5 text-green-400" />
                    <span className="ml-2 text-sm text-green-800">
                      {uploadedFile.name} ({(uploadedFile.size / 1024 / 1024).toFixed(2)} MB)
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* File Cleaning Utility Link */}
        <div className="mt-4 text-center">
          <div className="inline-flex items-center space-x-2 text-sm text-gray-600">
            <AlertCircle className="h-4 w-4" />
            <span>Having issues with your RVTool file?</span>
          </div>
          <div className="mt-2">
            <button
              onClick={() => navigate('/file-cleaning')}
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
            >
              <Settings className="h-4 w-4 mr-2" />
              Clean & Validate File
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Use our cleaning utility to fix common data issues before analysis
          </p>
        </div>
      </div>

      {/* Features Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card">
          <div className="card-content text-center">
            <FileText className="h-8 w-8 text-primary-600 mx-auto" />
            <h3 className="mt-2 text-lg font-medium text-gray-900">Migration Scope</h3>
            <p className="mt-1 text-sm text-gray-500">
              Identify blockers and classify workloads
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-content text-center">
            <BarChart3 className="h-8 w-8 text-primary-600 mx-auto" />
            <h3 className="mt-2 text-lg font-medium text-gray-900">Cost Estimates</h3>
            <p className="mt-1 text-sm text-gray-500">
              Real-time AWS pricing and TCO analysis
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-content text-center">
            <Zap className="h-8 w-8 text-primary-600 mx-auto" />
            <h3 className="mt-2 text-lg font-medium text-gray-900">Modernization</h3>
            <p className="mt-1 text-sm text-gray-500">
              AI-powered modernization opportunities
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-content text-center">
            <CheckCircle className="h-8 w-8 text-primary-600 mx-auto" />
            <h3 className="mt-2 text-lg font-medium text-gray-900">Reports</h3>
            <p className="mt-1 text-sm text-gray-500">
              Comprehensive analysis reports
            </p>
          </div>
        </div>
      </div>

      {/* Recent Sessions */}
      {state.sessions.length > 0 && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Analysis Sessions</h2>
          <div className="card">
            <div className="card-content">
              <div className="space-y-4">
                {state.sessions.map((session) => (
                  <div
                    key={session.session_id}
                    className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-2">
                        {getPhaseIcon(session.current_phase)}
                        <span className="text-sm font-medium text-gray-900">
                          {getPhaseLabel(session.current_phase)}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm text-gray-900">
                          Session {session.session_id.slice(0, 8)}...
                        </p>
                        <p className="text-xs text-gray-500">
                          {session.total_vms} VMs • Created {new Date(session.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleContinueSession(session.session_id)}
                        className="btn-primary"
                      >
                        <Play className="h-4 w-4 mr-1" />
                        Continue
                      </button>
                      <button
                        onClick={() => handleDeleteSession(session.session_id)}
                        className="btn-outline text-danger-600 hover:text-danger-700 hover:bg-danger-50"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Loading State */}
      {state.loading.isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <div className="flex items-center space-x-3">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
              <span className="text-gray-900">{state.loading.message || 'Loading...'}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
