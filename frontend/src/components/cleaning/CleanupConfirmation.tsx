import React, { useState } from 'react';
import { 
  Trash2, 
  AlertTriangle, 
  CheckCircle, 
  Settings,
  Info,
  Play
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

interface CleanupSelection {
  remove_duplicates: boolean;
  remove_null_values: boolean;
  remove_zero_values: boolean;
  remove_invalid_values: boolean;
  selected_rows_to_remove: number[];
  keep_first_duplicate: boolean;
}

interface CleanupConfirmationProps {
  session: CleaningSession;
  validationResult: DataValidationResult;
  onCleanup: (selection: CleanupSelection) => void;
  loading: boolean;
}

const CleanupConfirmation: React.FC<CleanupConfirmationProps> = ({
  session,
  validationResult,
  onCleanup,
  loading
}) => {
  const [cleanupSelection, setCleanupSelection] = useState<CleanupSelection>({
    remove_duplicates: true,
    remove_null_values: true,
    remove_zero_values: true,
    remove_invalid_values: true,
    selected_rows_to_remove: [],
    keep_first_duplicate: true
  });

  const [showAdvanced, setShowAdvanced] = useState(false);

  // Calculate impact
  const issuesByType = validationResult.issues.reduce((acc, issue) => {
    const type = issue.issue_type;
    if (!acc[type]) acc[type] = [];
    acc[type].push(issue);
    return acc;
  }, {} as Record<string, ValidationIssue[]>);

  const calculateRemovalImpact = () => {
    const rowsToRemove = new Set<number>();

    // Add duplicate rows
    if (cleanupSelection.remove_duplicates) {
      validationResult.duplicate_groups.forEach(group => {
        if (cleanupSelection.keep_first_duplicate) {
          group.slice(1).forEach(row => rowsToRemove.add(row));
        } else {
          group.forEach(row => rowsToRemove.add(row));
        }
      });
    }

    // Add issue rows based on selection
    validationResult.issues.forEach(issue => {
      let shouldRemove = false;
      
      switch (issue.issue_type) {
        case 'null_value':
          shouldRemove = cleanupSelection.remove_null_values;
          break;
        case 'zero_value':
          shouldRemove = cleanupSelection.remove_zero_values;
          break;
        case 'invalid_value':
          shouldRemove = cleanupSelection.remove_invalid_values;
          break;
      }

      if (shouldRemove) {
        rowsToRemove.add(issue.row_index);
      }
    });

    // Add manually selected rows
    cleanupSelection.selected_rows_to_remove.forEach(row => rowsToRemove.add(row));

    return {
      rowsToRemove: Array.from(rowsToRemove).sort((a, b) => a - b),
      totalToRemove: rowsToRemove.size,
      remainingRecords: validationResult.total_records - rowsToRemove.size
    };
  };

  const impact = calculateRemovalImpact();

  const handleCleanup = () => {
    onCleanup(cleanupSelection);
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

  return (
    <div className="p-8">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Confirm Data Cleanup
        </h2>
        <p className="text-gray-600">
          Review and configure which issues to fix automatically
        </p>
      </div>

      <div className="space-y-6">
        {/* Cleanup Options */}
        <div className="bg-white border rounded-lg">
          <div className="px-6 py-4 border-b bg-gray-50">
            <h3 className="text-lg font-medium text-gray-900">Cleanup Options</h3>
          </div>
          <div className="p-6 space-y-4">
            {/* Duplicates */}
            {validationResult.duplicate_groups.length > 0 && (
              <div className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  id="remove_duplicates"
                  checked={cleanupSelection.remove_duplicates}
                  onChange={(e) => setCleanupSelection(prev => ({
                    ...prev,
                    remove_duplicates: e.target.checked
                  }))}
                  className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <div className="flex-1">
                  <label htmlFor="remove_duplicates" className="text-sm font-medium text-gray-900">
                    Remove Duplicate Records
                  </label>
                  <p className="text-sm text-gray-600">
                    Found {validationResult.duplicate_groups.length} duplicate groups affecting{' '}
                    {validationResult.duplicate_groups.reduce((sum, group) => sum + group.length, 0)} records
                  </p>
                  {cleanupSelection.remove_duplicates && (
                    <div className="mt-2">
                      <label className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          checked={cleanupSelection.keep_first_duplicate}
                          onChange={(e) => setCleanupSelection(prev => ({
                            ...prev,
                            keep_first_duplicate: e.target.checked
                          }))}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                        <span className="text-sm text-gray-700">Keep first occurrence of duplicates</span>
                      </label>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Null Values */}
            {issuesByType.null_value && (
              <div className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  id="remove_null_values"
                  checked={cleanupSelection.remove_null_values}
                  onChange={(e) => setCleanupSelection(prev => ({
                    ...prev,
                    remove_null_values: e.target.checked
                  }))}
                  className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <div className="flex-1">
                  <label htmlFor="remove_null_values" className="text-sm font-medium text-gray-900">
                    Remove Records with Null Values
                  </label>
                  <p className="text-sm text-gray-600">
                    Found {issuesByType.null_value.length} records with null values in critical columns (VM, CPUs, OS according to the configuration file)
                  </p>
                </div>
              </div>
            )}

            {/* Zero Values */}
            {issuesByType.zero_value && (
              <div className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  id="remove_zero_values"
                  checked={cleanupSelection.remove_zero_values}
                  onChange={(e) => setCleanupSelection(prev => ({
                    ...prev,
                    remove_zero_values: e.target.checked
                  }))}
                  className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <div className="flex-1">
                  <label htmlFor="remove_zero_values" className="text-sm font-medium text-gray-900">
                    Remove Records with Zero Values
                  </label>
                  <p className="text-sm text-gray-600">
                    Found {issuesByType.zero_value.length} records with zero values in CPUs
                  </p>
                </div>
              </div>
            )}

            {/* Invalid Values */}
            {issuesByType.invalid_value && (
              <div className="flex items-start space-x-3">
                <input
                  type="checkbox"
                  id="remove_invalid_values"
                  checked={cleanupSelection.remove_invalid_values}
                  onChange={(e) => setCleanupSelection(prev => ({
                    ...prev,
                    remove_invalid_values: e.target.checked
                  }))}
                  className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <div className="flex-1">
                  <label htmlFor="remove_invalid_values" className="text-sm font-medium text-gray-900">
                    Remove Records with Invalid Values
                  </label>
                  <p className="text-sm text-gray-600">
                    Found {issuesByType.invalid_value.length} records with values outside expected ranges
                  </p>
                </div>
              </div>
            )}

            {/* Advanced Options */}
            <div className="pt-4 border-t">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-700"
              >
                <Settings className="w-4 h-4" />
                <span>Advanced Options</span>
              </button>

              {showAdvanced && (
                <div className="mt-4 p-4 bg-gray-50 rounded-md">
                  <p className="text-sm text-gray-600 mb-3">
                    Manually select specific rows to remove (comma-separated row numbers):
                  </p>
                  <input
                    type="text"
                    placeholder="e.g., 5, 12, 23"
                    value={cleanupSelection.selected_rows_to_remove.join(', ')}
                    onChange={(e) => {
                      const rows = e.target.value
                        .split(',')
                        .map(s => parseInt(s.trim()) - 1)
                        .filter(n => !isNaN(n) && n >= 0);
                      setCleanupSelection(prev => ({
                        ...prev,
                        selected_rows_to_remove: rows
                      }));
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Impact Summary */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-6 h-6 text-yellow-500 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-lg font-medium text-yellow-800 mb-3">
                Cleanup Impact Summary
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-md p-3">
                  <div className="text-center">
                    <div className="text-xl font-bold text-gray-900">
                      {validationResult.total_records}
                    </div>
                    <div className="text-sm text-gray-600">Original Records</div>
                  </div>
                </div>
                <div className="bg-white rounded-md p-3">
                  <div className="text-center">
                    <div className="text-xl font-bold text-red-600">
                      {impact.totalToRemove}
                    </div>
                    <div className="text-sm text-gray-600">Records to Remove</div>
                  </div>
                </div>
                <div className="bg-white rounded-md p-3">
                  <div className="text-center">
                    <div className="text-xl font-bold text-green-600">
                      {impact.remainingRecords}
                    </div>
                    <div className="text-sm text-gray-600">Remaining Records</div>
                  </div>
                </div>
              </div>
              
              {impact.totalToRemove > 0 && (
                <div className="mt-4 p-3 bg-yellow-100 rounded-md">
                  <p className="text-sm text-yellow-800">
                    <strong>Warning:</strong> This action will permanently remove {impact.totalToRemove} records 
                    ({((impact.totalToRemove / validationResult.total_records) * 100).toFixed(1)}% of your data). 
                    Make sure you have a backup of your original file.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-2 text-sm text-gray-600">
            <Info className="w-4 h-4" />
            <span>
              {impact.totalToRemove === 0 
                ? 'No records will be removed with current settings'
                : `${impact.totalToRemove} records will be removed`
              }
            </span>
          </div>
          
          <button
            onClick={handleCleanup}
            disabled={loading}
            className={`
              inline-flex items-center px-6 py-3 rounded-md font-medium transition-colors
              ${loading
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : impact.totalToRemove > 0
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : 'bg-green-600 text-white hover:bg-green-700'
              }
            `}
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Processing Cleanup...
              </>
            ) : (
              <>
                {impact.totalToRemove > 0 ? (
                  <Trash2 className="w-4 h-4 mr-2" />
                ) : (
                  <CheckCircle className="w-4 h-4 mr-2" />
                )}
                {impact.totalToRemove > 0 ? 'Clean Data' : 'Proceed to Download'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CleanupConfirmation;
