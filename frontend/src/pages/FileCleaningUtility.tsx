import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Upload,
  FileText,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Download,
  ArrowLeft,
  RefreshCw,
  Trash2,
  Info
} from 'lucide-react';

// Import cleaning components
import FileUploadSection from '../components/cleaning/FileUploadSection';
import HeaderValidation from '../components/cleaning/HeaderValidation';
import DataValidationResults from '../components/cleaning/DataValidationResults';
import CleanupConfirmation from '../components/cleaning/CleanupConfirmation';
import FileExportSection from '../components/cleaning/FileExportSection';

// Import cleaning API service
import { cleaningApiService } from '../services/cleaningApi';

// Types
interface CleaningSession {
  session_id: string;
  original_filename: string;
  file_size: number;
  status: string;
  header_validation?: any;
  data_validation?: any;
  cleanup_result?: any;
}

interface ValidationResults {
  header_validation?: any;
  data_validation?: any;
}

const FileCleaningUtility: React.FC = () => {
  const navigate = useNavigate();
  
  // State management
  const [currentStep, setCurrentStep] = useState<'upload' | 'header' | 'data' | 'cleanup' | 'export'>('upload');
  const [session, setSession] = useState<CleaningSession | null>(null);
  const [validationResults, setValidationResults] = useState<ValidationResults>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step navigation
  const steps = [
    { key: 'upload', label: 'Upload File', icon: Upload },
    { key: 'header', label: 'Validate Headers', icon: FileText },
    { key: 'data', label: 'Validate Data', icon: CheckCircle },
    { key: 'cleanup', label: 'Clean Data', icon: RefreshCw },
    { key: 'export', label: 'Download', icon: Download }
  ];

  const currentStepIndex = steps.findIndex(step => step.key === currentStep);

  // Handlers
  const handleFileUpload = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await cleaningApiService.uploadFile(file);
      setSession(response.session);
      setCurrentStep('header');
    } catch (err: any) {
      setError(err.message || 'Failed to upload file');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleHeaderValidation = useCallback(async () => {
    if (!session) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await cleaningApiService.validateHeaders(session.session_id);
      setValidationResults(prev => ({ ...prev, header_validation: response.header_validation }));
      
      // Don't auto-navigate - let user review results and manually proceed
      if (!response.header_validation.is_valid) {
        setError('Header validation failed. Please check the required columns.');
      }
    } catch (err: any) {
      setError(err.message || 'Header validation failed');
    } finally {
      setLoading(false);
    }
  }, [session]);

  const handleProceedToDataValidation = useCallback(() => {
    // Manual navigation to data validation step
    if (validationResults.header_validation?.is_valid) {
      setCurrentStep('data');
    }
  }, [validationResults.header_validation]);

  const handleDataValidation = useCallback(async () => {
    if (!session) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await cleaningApiService.validateData(session.session_id);
      setValidationResults(prev => ({ ...prev, data_validation: response.data_validation }));
      setCurrentStep('cleanup');
    } catch (err: any) {
      setError(err.message || 'Data validation failed');
    } finally {
      setLoading(false);
    }
  }, [session]);

  const handleCleanup = useCallback(async (cleanupSelection: any) => {
    if (!session) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await cleaningApiService.cleanupData(session.session_id, cleanupSelection);
      setSession(prev => prev ? { ...prev, cleanup_result: response.cleanup_result } : null);
      setCurrentStep('export');
    } catch (err: any) {
      setError(err.message || 'Data cleanup failed');
    } finally {
      setLoading(false);
    }
  }, [session]);

  const handleReset = useCallback(() => {
    setCurrentStep('upload');
    setSession(null);
    setValidationResults({});
    setError(null);
  }, []);

  const getStepStatus = (stepKey: string) => {
    const stepIndex = steps.findIndex(step => step.key === stepKey);
    if (stepIndex < currentStepIndex) return 'completed';
    if (stepIndex === currentStepIndex) return 'current';
    return 'pending';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center text-gray-600 hover:text-gray-900 mr-4"
              >
                <ArrowLeft className="h-5 w-5 mr-2" />
                Back to Dashboard
              </button>
              <h1 className="text-xl font-semibold text-gray-900">
                RVTool File Cleaning Utility
              </h1>
            </div>
            <button
              onClick={handleReset}
              className="flex items-center px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Start Over
            </button>
          </div>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-4">
            <nav className="flex items-center justify-center">
              <ol className="flex items-center space-x-8">
                {steps.map((step, index) => {
                  const status = getStepStatus(step.key);
                  const Icon = step.icon;
                  
                  return (
                    <li key={step.key} className="flex items-center">
                      <div className={`
                        flex items-center justify-center w-10 h-10 rounded-full border-2
                        ${status === 'completed' ? 'bg-green-100 border-green-500 text-green-600' :
                          status === 'current' ? 'bg-blue-100 border-blue-500 text-blue-600' :
                          'bg-gray-100 border-gray-300 text-gray-400'}
                      `}>
                        {status === 'completed' ? (
                          <CheckCircle className="h-5 w-5" />
                        ) : (
                          <Icon className="h-5 w-5" />
                        )}
                      </div>
                      <span className={`
                        ml-3 text-sm font-medium
                        ${status === 'current' ? 'text-blue-600' :
                          status === 'completed' ? 'text-green-600' :
                          'text-gray-500'}
                      `}>
                        {step.label}
                      </span>
                      {index < steps.length - 1 && (
                        <div className={`
                          ml-8 w-8 h-0.5
                          ${status === 'completed' ? 'bg-green-500' : 'bg-gray-300'}
                        `} />
                      )}
                    </li>
                  );
                })}
              </ol>
            </nav>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <XCircle className="h-5 w-5 text-red-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Error</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Step Content */}
        <div className="bg-white rounded-lg shadow">
          {currentStep === 'upload' && (
            <FileUploadSection
              onFileUpload={handleFileUpload}
              loading={loading}
            />
          )}

          {currentStep === 'header' && session && (
            <HeaderValidation
              session={session}
              validationResult={validationResults.header_validation}
              onValidate={handleHeaderValidation}
              onProceedToDataValidation={handleProceedToDataValidation}
              loading={loading}
            />
          )}

          {currentStep === 'data' && session && (
            <DataValidationResults
              session={session}
              validationResult={validationResults.data_validation}
              onValidate={handleDataValidation}
              loading={loading}
            />
          )}

          {currentStep === 'cleanup' && session && validationResults.data_validation && (
            <CleanupConfirmation
              session={session}
              validationResult={validationResults.data_validation}
              onCleanup={handleCleanup}
              loading={loading}
            />
          )}

          {currentStep === 'export' && session && session.cleanup_result && (
            <FileExportSection
              session={session}
              cleanupResult={session.cleanup_result}
            />
          )}
        </div>

        {/* Help Information */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="flex">
            <Info className="h-5 w-5 text-blue-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">About File Cleaning</h3>
              <div className="mt-2 text-sm text-blue-700">
                <p>This utility helps you clean and validate RVTool files before uploading them to the main analysis platform:</p>
                <ul className="mt-2 list-disc list-inside space-y-1">
                  <li>Validates required column headers for TCO calculations</li>
                  <li>Identifies duplicate VM entries</li>
                  <li>Detects null, zero, and invalid values in critical fields</li>
                  <li>Allows you to review and remove problematic records</li>
                  <li>Generates a cleaned file ready for analysis</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileCleaningUtility;
