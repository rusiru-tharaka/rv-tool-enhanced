import React from 'react';
import { CheckCircle, XCircle, AlertTriangle, FileText, Play, ArrowRight } from 'lucide-react';

interface HeaderValidationResult {
  is_valid: boolean;
  missing_headers: string[];
  extra_headers: string[];
  total_columns: number;
  required_columns_found: number;
}

interface CleaningSession {
  session_id: string;
  original_filename: string;
  file_size: number;
  status: string;
}

interface HeaderValidationProps {
  session: CleaningSession;
  validationResult?: HeaderValidationResult;
  onValidate: () => void;
  onProceedToDataValidation: () => void;
  loading: boolean;
}

const HeaderValidation: React.FC<HeaderValidationProps> = ({
  session,
  validationResult,
  onValidate,
  onProceedToDataValidation,
  loading
}) => {
  const requiredColumns = [
    'VM',                                    // VM Name
    'CPUs',                                  // vCPUs  
    'Powerstate',                           // Power State
    'In Use MiB',                          // Storage (Consumed) - Primary
    'Provisioned MiB',                      // Storage (Provisioned) - Fallback
    'OS according to the configuration file', // Operating System (UPDATED)
    'Cluster',                             // VM Cluster
    'Host'                                 // VM Host
  ];

  const getColumnDescription = (column: string): string => {
    const descriptions: Record<string, string> = {
      'VM': 'VM Name',
      'CPUs': 'vCPUs',
      'Powerstate': 'Power State',
      'In Use MiB': 'Storage (Consumed)',
      'Provisioned MiB': 'Storage (Provisioned)',
      'OS according to the configuration file': 'Operating System',
      'Cluster': 'VM Cluster',
      'Host': 'VM Host'
    };
    return descriptions[column] || column;
  };

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
          Validate Column Headers
        </h2>
        <p className="text-gray-600">
          Checking if your file contains all required columns for TCO calculations
        </p>
      </div>

      {/* File Info */}
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <div className="flex items-center space-x-3">
          <FileText className="w-6 h-6 text-blue-500" />
          <div>
            <p className="font-medium text-gray-900">{session.original_filename}</p>
            <p className="text-sm text-gray-500">{formatFileSize(session.file_size)}</p>
          </div>
        </div>
      </div>

      {/* Validation Action */}
      {!validationResult && (
        <div className="text-center mb-8">
          <button
            onClick={onValidate}
            disabled={loading}
            className={`
              inline-flex items-center px-6 py-3 rounded-md font-medium transition-colors
              ${loading
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
              }
            `}
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Validating Headers...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Validate Headers
              </>
            )}
          </button>
        </div>
      )}

      {/* Validation Results */}
      {validationResult && (
        <div className="space-y-6">
          {/* Overall Status */}
          <div className={`
            rounded-lg p-4 border
            ${validationResult.is_valid
              ? 'bg-green-50 border-green-200'
              : 'bg-red-50 border-red-200'
            }
          `}>
            <div className="flex items-center space-x-3">
              {validationResult.is_valid ? (
                <CheckCircle className="w-6 h-6 text-green-500" />
              ) : (
                <XCircle className="w-6 h-6 text-red-500" />
              )}
              <div>
                <h3 className={`font-medium ${
                  validationResult.is_valid ? 'text-green-800' : 'text-red-800'
                }`}>
                  {validationResult.is_valid 
                    ? 'Header Validation Passed' 
                    : 'Header Validation Failed'
                  }
                </h3>
                <p className={`text-sm ${
                  validationResult.is_valid ? 'text-green-700' : 'text-red-700'
                }`}>
                  {validationResult.is_valid
                    ? 'All required columns are present in your file'
                    : `Missing ${validationResult.missing_headers.length} required column(s)`
                  }
                </p>
              </div>
            </div>
          </div>

          {/* Column Statistics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {validationResult.total_columns}
                </div>
                <div className="text-sm text-blue-800">Total Columns</div>
              </div>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {validationResult.required_columns_found}
                </div>
                <div className="text-sm text-green-800">Required Found</div>
              </div>
            </div>
            <div className="bg-yellow-50 rounded-lg p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {validationResult.extra_headers.length}
                </div>
                <div className="text-sm text-yellow-800">Extra Columns</div>
              </div>
            </div>
          </div>

          {/* Required Columns Status */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Required Columns Status
            </h3>
            <div className="grid grid-cols-1 gap-3">
              {requiredColumns.map((column) => {
                const isPresent = !validationResult.missing_headers.includes(column);
                const description = getColumnDescription(column);
                return (
                  <div
                    key={column}
                    className={`
                      flex items-center justify-between p-3 rounded-lg border
                      ${isPresent
                        ? 'bg-green-50 border-green-200'
                        : 'bg-red-50 border-red-200'
                      }
                    `}
                  >
                    <div className="flex items-center space-x-3">
                      {isPresent ? (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-500" />
                      )}
                      <div>
                        <span className={`font-medium ${
                          isPresent ? 'text-green-800' : 'text-red-800'
                        }`}>
                          {column}
                        </span>
                        <div className={`text-sm ${
                          isPresent ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {description}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Missing Headers Alert */}
          {validationResult.missing_headers.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5" />
                <div>
                  <h3 className="font-medium text-red-800 mb-2">
                    Missing Required Columns
                  </h3>
                  <p className="text-sm text-red-700 mb-3">
                    The following columns are required for TCO calculations but are missing from your file:
                  </p>
                  <ul className="text-sm text-red-700 space-y-1">
                    {validationResult.missing_headers.map((header) => (
                      <li key={header} className="flex items-center space-x-2">
                        <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
                        <span className="font-medium">{header}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="mt-4 p-3 bg-red-100 rounded-md">
                    <p className="text-sm text-red-800">
                      <strong>Action Required:</strong> Please update your RVTool export to include these columns, 
                      or modify your file to add the missing columns before proceeding.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Extra Headers Info */}
          {validationResult.extra_headers.length > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-yellow-500 mt-0.5" />
                <div>
                  <h3 className="font-medium text-yellow-800 mb-2">
                    Additional Columns Found ({validationResult.extra_headers.length})
                  </h3>
                  <p className="text-sm text-yellow-700 mb-3">
                    These columns are not required for TCO calculations but will be preserved in the cleaned file:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {validationResult.extra_headers.slice(0, 10).map((header) => (
                      <span
                        key={header}
                        className="inline-flex items-center px-2 py-1 rounded-md bg-yellow-100 text-yellow-800 text-xs font-medium"
                      >
                        {header}
                      </span>
                    ))}
                    {validationResult.extra_headers.length > 10 && (
                      <span className="inline-flex items-center px-2 py-1 rounded-md bg-yellow-100 text-yellow-800 text-xs font-medium">
                        +{validationResult.extra_headers.length - 10} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Next Steps */}
          {validationResult.is_valid && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-green-500" />
                  <div>
                    <h3 className="font-medium text-green-800">Header Validation Passed</h3>
                    <p className="text-sm text-green-700">
                      All required columns are present. You can now proceed to validate the data content.
                    </p>
                  </div>
                </div>
                <button
                  onClick={onProceedToDataValidation}
                  className="inline-flex items-center px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 transition-colors"
                >
                  Proceed to Data Validation
                  <ArrowRight className="w-4 h-4 ml-2" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default HeaderValidation;
