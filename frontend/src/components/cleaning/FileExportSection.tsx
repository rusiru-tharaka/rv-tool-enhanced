import React, { useState } from 'react';
import { 
  Download, 
  CheckCircle, 
  FileText, 
  BarChart3,
  ArrowRight,
  ExternalLink
} from 'lucide-react';
import { cleaningApiService } from '../../services/cleaningApi';

interface CleanupResult {
  original_record_count: number;
  cleaned_record_count: number;
  removed_record_count: number;
  removed_rows: number[];
  cleanup_summary: Record<string, number>;
}

interface CleaningSession {
  session_id: string;
  original_filename: string;
  file_size: number;
  status: string;
  cleaned_filename?: string;
}

interface FileExportSectionProps {
  session: CleaningSession;
  cleanupResult: CleanupResult;
}

const FileExportSection: React.FC<FileExportSectionProps> = ({
  session,
  cleanupResult
}) => {
  const [downloading, setDownloading] = useState(false);
  const [downloadingRemoved, setDownloadingRemoved] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await cleaningApiService.downloadCleanedFile(session.session_id);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadRemovedData = async () => {
    setDownloadingRemoved(true);
    try {
      await cleaningApiService.downloadRemovedData(session.session_id);
    } catch (error) {
      console.error('Download removed data failed:', error);
      alert('Download removed data failed. Please try again.');
    } finally {
      setDownloadingRemoved(false);
    }
  };

  const getCleanupSummaryItems = () => {
    const items = [];
    const summary = cleanupResult.cleanup_summary;

    if (summary.duplicates_removed) {
      items.push({
        label: 'Duplicate Records',
        count: summary.duplicates_removed,
        color: 'text-yellow-600 bg-yellow-50'
      });
    }

    if (summary.null_value) {
      items.push({
        label: 'Null Values',
        count: summary.null_value,
        color: 'text-red-600 bg-red-50'
      });
    }

    if (summary.zero_value) {
      items.push({
        label: 'Zero Values',
        count: summary.zero_value,
        color: 'text-orange-600 bg-orange-50'
      });
    }

    if (summary.invalid_value) {
      items.push({
        label: 'Invalid Values',
        count: summary.invalid_value,
        color: 'text-purple-600 bg-purple-50'
      });
    }

    return items;
  };

  const cleanupSummaryItems = getCleanupSummaryItems();
  const removalPercentage = ((cleanupResult.removed_record_count / cleanupResult.original_record_count) * 100).toFixed(1);

  return (
    <div className="p-8">
      <div className="text-center mb-8">
        <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
          <CheckCircle className="w-8 h-8 text-green-500" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          File Cleaning Complete!
        </h2>
        <p className="text-gray-600">
          Your RVTool file has been successfully cleaned and is ready for download
        </p>
      </div>

      <div className="space-y-6">
        {/* Cleanup Results Summary */}
        <div className="bg-white border rounded-lg">
          <div className="px-6 py-4 border-b bg-gray-50">
            <h3 className="text-lg font-medium text-gray-900">Cleanup Results</h3>
          </div>
          <div className="p-6">
            {/* Statistics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-blue-50 rounded-lg p-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {cleanupResult.original_record_count}
                  </div>
                  <div className="text-sm text-blue-800">Original Records</div>
                </div>
              </div>
              <div className="bg-red-50 rounded-lg p-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {cleanupResult.removed_record_count}
                  </div>
                  <div className="text-sm text-red-800">Records Removed</div>
                  <div className="text-xs text-red-600 mt-1">
                    ({removalPercentage}%)
                  </div>
                </div>
              </div>
              <div className="bg-green-50 rounded-lg p-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {cleanupResult.cleaned_record_count}
                  </div>
                  <div className="text-sm text-green-800">Clean Records</div>
                  <div className="text-xs text-green-600 mt-1">
                    ({(100 - parseFloat(removalPercentage)).toFixed(1)}%)
                  </div>
                </div>
              </div>
            </div>

            {/* Cleanup Details */}
            {cleanupSummaryItems.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">Issues Resolved:</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {cleanupSummaryItems.map((item, index) => (
                    <div key={index} className={`rounded-md p-3 ${item.color}`}>
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{item.label}</span>
                        <span className="text-sm font-bold">{item.count} removed</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* File Information */}
        <div className="bg-white border rounded-lg">
          <div className="px-6 py-4 border-b bg-gray-50">
            <h3 className="text-lg font-medium text-gray-900">Cleaned File</h3>
          </div>
          <div className="p-6">
            <div className="flex items-center space-x-4">
              <div className="flex-shrink-0">
                <FileText className="w-10 h-10 text-blue-500" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  {session.cleaned_filename || `cleaned_${session.original_filename}`}
                </p>
                <p className="text-sm text-gray-500">
                  Ready for download • {cleanupResult.cleaned_record_count} records
                </p>
              </div>
              <div className="flex-shrink-0">
                <button
                  onClick={handleDownload}
                  disabled={downloading}
                  className={`
                    inline-flex items-center px-4 py-2 rounded-md font-medium transition-colors
                    ${downloading
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                    }
                  `}
                >
                  {downloading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Downloading...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      Download
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Removed Data Download */}
        {cleanupResult.removed_record_count > 0 && (
          <div className="bg-white border rounded-lg">
            <div className="px-6 py-4 border-b bg-gray-50">
              <h3 className="text-lg font-medium text-gray-900">Removed Data Report</h3>
            </div>
            <div className="p-6">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  <FileText className="w-10 h-10 text-orange-500" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    removed_data_{session.original_filename}
                  </p>
                  <p className="text-sm text-gray-500">
                    Contains {cleanupResult.removed_record_count} removed records with cleanup reasons
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <button
                    onClick={handleDownloadRemovedData}
                    disabled={downloadingRemoved}
                    className={`
                      inline-flex items-center px-4 py-2 rounded-md font-medium transition-colors
                      ${downloadingRemoved
                        ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        : 'bg-orange-600 text-white hover:bg-orange-700'
                      }
                    `}
                  >
                    {downloadingRemoved ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Downloading...
                      </>
                    ) : (
                      <>
                        <FileText className="w-4 h-4 mr-2" />
                        Download Report
                      </>
                    )}
                  </button>
                </div>
              </div>
              <div className="mt-4 p-3 bg-orange-50 rounded-md">
                <p className="text-sm text-orange-800">
                  <strong>What's included:</strong> All removed records with their original data, 
                  row numbers, and detailed reasons for removal (duplicates, null values, zero values, etc.)
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Next Steps */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-blue-800 mb-4">What's Next?</h3>
          <div className="space-y-4">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                1
              </div>
              <div>
                <p className="text-sm font-medium text-blue-800">Download Your Cleaned File</p>
                <p className="text-sm text-blue-700">
                  Click the download button above to get your cleaned RVTool file
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                2
              </div>
              <div>
                <p className="text-sm font-medium text-blue-800">Upload to Main Analysis</p>
                <p className="text-sm text-blue-700">
                  Use the cleaned file in the main RVTool analysis platform for accurate TCO calculations
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-medium">
                3
              </div>
              <div>
                <p className="text-sm font-medium text-blue-800">Review Results</p>
                <p className="text-sm text-blue-700">
                  The cleaned data will provide more accurate migration cost estimates and recommendations
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={handleDownload}
            disabled={downloading}
            className={`
              inline-flex items-center justify-center px-6 py-3 rounded-md font-medium transition-colors
              ${downloading
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
              }
            `}
          >
            {downloading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Downloading...
              </>
            ) : (
              <>
                <Download className="w-5 h-5 mr-2" />
                Download Cleaned File
              </>
            )}
          </button>

          <button
            onClick={() => window.location.href = '/dashboard'}
            className="inline-flex items-center justify-center px-6 py-3 rounded-md font-medium border border-gray-300 text-gray-700 bg-white hover:bg-gray-50 transition-colors"
          >
            <BarChart3 className="w-5 h-5 mr-2" />
            Go to Analysis Dashboard
            <ArrowRight className="w-4 h-4 ml-2" />
          </button>
        </div>

        {/* Success Message */}
        <div className="text-center">
          <div className="inline-flex items-center space-x-2 text-green-600">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">
              File cleaning completed successfully! Your data is now ready for analysis.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FileExportSection;
