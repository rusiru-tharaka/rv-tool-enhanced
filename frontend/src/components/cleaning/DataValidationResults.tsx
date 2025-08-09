import React, { useState } from 'react';
import { 
  AlertTriangle, 
  XCircle, 
  CheckCircle, 
  Play, 
  Eye, 
  EyeOff,
  Info,
  AlertCircle
} from 'lucide-react';

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

interface CleaningSession {
  session_id: string;
  original_filename: string;
  file_size: number;
  status: string;
}

interface DataValidationResultsProps {
  session: CleaningSession;
  validationResult?: DataValidationResult;
  onValidate: () => void;
  loading: boolean;
}

const DataValidationResults: React.FC<DataValidationResultsProps> = ({
  session,
  validationResult,
  onValidate,
  loading
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [selectedIssueType, setSelectedIssueType] = useState<string>('all');

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return 'text-red-600 bg-red-50 border-red-200';
      case 'high': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'medium': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low': return 'text-blue-600 bg-blue-50 border-blue-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical': return <XCircle className="w-4 h-4" />;
      case 'high': return <AlertTriangle className="w-4 h-4" />;
      case 'medium': return <AlertCircle className="w-4 h-4" />;
      case 'low': return <Info className="w-4 h-4" />;
      default: return <Info className="w-4 h-4" />;
    }
  };

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

  const getIssueTypeLabel = (issueType: string) => {
    switch (issueType) {
      case 'duplicate_record': return 'Duplicate Records';
      case 'null_value': return 'Null Values';
      case 'zero_value': return 'Zero Values';
      case 'invalid_value': return 'Invalid Values';
      case 'logical_error': return 'Logical Errors';
      default: return issueType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
  };

  // Group issues by type
  const issuesByType = validationResult?.issues.reduce((acc, issue) => {
    const type = issue.issue_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(issue);
    return acc;
  }, {} as Record<string, ValidationIssue[]>) || {};

  // Filter issues based on selected type
  const filteredIssues = selectedIssueType === 'all' 
    ? validationResult?.issues || []
    : issuesByType[selectedIssueType] || [];

  const criticalIssuesCount = validationResult?.issues.filter(i => i.severity === 'critical').length || 0;

  return (
    <div className="p-8">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Data Validation Results
        </h2>
        <p className="text-gray-600">
          Checking for duplicates, null values, and data quality issues
        </p>
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
                Validating Data...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Validate Data
              </>
            )}
          </button>
        </div>
      )}

      {/* Validation Results */}
      {validationResult && (
        <div className="space-y-6">
          {/* Overall Statistics */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {validationResult.total_records}
                </div>
                <div className="text-sm text-blue-800">Total Records</div>
              </div>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {validationResult.valid_records}
                </div>
                <div className="text-sm text-green-800">Valid Records</div>
              </div>
            </div>
            <div className="bg-yellow-50 rounded-lg p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">
                  {validationResult.issues.length}
                </div>
                <div className="text-sm text-yellow-800">Total Issues</div>
              </div>
            </div>
            <div className="bg-red-50 rounded-lg p-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">
                  {criticalIssuesCount}
                </div>
                <div className="text-sm text-red-800">Critical Issues</div>
              </div>
            </div>
          </div>

          {/* Issues Summary */}
          {validationResult.issues.length > 0 ? (
            <>
              {/* Issue Type Filter */}
              <div className="flex flex-wrap gap-2 mb-4">
                <button
                  onClick={() => setSelectedIssueType('all')}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                    selectedIssueType === 'all'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  All Issues ({validationResult.issues.length})
                </button>
                {Object.entries(issuesByType).map(([type, issues]) => (
                  <button
                    key={type}
                    onClick={() => setSelectedIssueType(type)}
                    className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                      selectedIssueType === type
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {getIssueTypeLabel(type)} ({issues.length})
                  </button>
                ))}
              </div>

              {/* Issues List */}
              <div className="bg-white border rounded-lg">
                <div className="px-4 py-3 border-b bg-gray-50">
                  <h3 className="text-lg font-medium text-gray-900">
                    {selectedIssueType === 'all' 
                      ? `All Issues (${filteredIssues.length})`
                      : `${getIssueTypeLabel(selectedIssueType)} (${filteredIssues.length})`
                    }
                  </h3>
                </div>
                <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
                  {filteredIssues.slice(0, 100).map((issue, index) => (
                    <div key={index} className="p-4">
                      <div className="flex items-start space-x-3">
                        <div className={`
                          flex items-center justify-center w-6 h-6 rounded-full border
                          ${getSeverityColor(issue.severity)}
                        `}>
                          {getSeverityIcon(issue.severity)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium text-gray-900">
                              Row {issue.row_index + 1} - {getColumnDescription(issue.column)}
                            </p>
                            <span className={`
                              inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border
                              ${getSeverityColor(issue.severity)}
                            `}>
                              {issue.severity.toUpperCase()}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">
                            {issue.description}
                          </p>
                          <div className="mt-2 text-xs text-gray-500">
                            <span className="font-medium">Column:</span> {issue.column}
                            <span className="mx-2">•</span>
                            <span className="font-medium">Current value:</span> {
                              issue.current_value === null || issue.current_value === undefined 
                                ? '(null)' 
                                : String(issue.current_value)
                            }
                            {issue.expected_value && (
                              <>
                                <span className="mx-2">•</span>
                                <span className="font-medium">Expected:</span> {issue.expected_value}
                              </>
                            )}
                          </div>
                          {issue.suggestion && (
                            <div className="mt-2 p-2 bg-blue-50 rounded-md">
                              <p className="text-xs text-blue-700">
                                <span className="font-medium">Suggestion:</span> {issue.suggestion}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  {filteredIssues.length > 100 && (
                    <div className="p-4 text-center text-sm text-gray-500">
                      Showing first 100 issues. {filteredIssues.length - 100} more issues found.
                    </div>
                  )}
                </div>
              </div>

              {/* Duplicate Groups */}
              {validationResult.duplicate_groups.length > 0 && (
                <div className="bg-white border rounded-lg">
                  <div className="px-4 py-3 border-b bg-gray-50">
                    <button
                      onClick={() => toggleSection('duplicates')}
                      className="flex items-center justify-between w-full text-left"
                    >
                      <h3 className="text-lg font-medium text-gray-900">
                        Duplicate Groups ({validationResult.duplicate_groups.length})
                      </h3>
                      {expandedSections.has('duplicates') ? (
                        <EyeOff className="w-5 h-5 text-gray-400" />
                      ) : (
                        <Eye className="w-5 h-5 text-gray-400" />
                      )}
                    </button>
                  </div>
                  {expandedSections.has('duplicates') && (
                    <div className="p-4">
                      <div className="space-y-3">
                        {validationResult.duplicate_groups.slice(0, 10).map((group, index) => (
                          <div key={index} className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                            <p className="text-sm font-medium text-yellow-800">
                              Duplicate Group {index + 1}
                            </p>
                            <p className="text-sm text-yellow-700">
                              Rows: {group.map(row => row + 1).join(', ')}
                            </p>
                          </div>
                        ))}
                        {validationResult.duplicate_groups.length > 10 && (
                          <p className="text-sm text-gray-500 text-center">
                            Showing first 10 duplicate groups. {validationResult.duplicate_groups.length - 10} more found.
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            /* No Issues Found */
            <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-green-800 mb-2">
                No Data Issues Found!
              </h3>
              <p className="text-green-700">
                Your data looks clean and ready for analysis. All records passed validation checks.
              </p>
            </div>
          )}

          {/* Next Steps */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center space-x-3">
              <Info className="w-5 h-5 text-blue-500" />
              <div>
                <h3 className="font-medium text-blue-800">Next Steps</h3>
                <p className="text-sm text-blue-700">
                  {validationResult.issues.length > 0
                    ? 'Review the issues above and proceed to cleanup to remove problematic records.'
                    : 'Your data is clean and ready. You can proceed to download the file or continue with cleanup if needed.'
                  }
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataValidationResults;
