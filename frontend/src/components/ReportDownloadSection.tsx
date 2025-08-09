import React, { useState } from 'react';
import { 
  Download, 
  FileText, 
  Loader, 
  AlertTriangle, 
  BarChart3, 
  Calendar, 
  Server,
  CheckCircle,
  XCircle
} from 'lucide-react';
import apiService from '../services/api';
import { AIBadge, AIProcessingIndicator } from './AIIndicators';

interface ReportDownloadSectionProps {
  sessionId: string;
}

interface ReportType {
  type: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
}

const ReportDownloadSection: React.FC<ReportDownloadSectionProps> = ({ sessionId }) => {
  const [downloadingReport, setDownloadingReport] = useState<string | null>(null);
  const [downloadStatus, setDownloadStatus] = useState<Record<string, 'success' | 'error' | null>>({});

  const reportTypes: ReportType[] = [
    {
      type: 'migration-blockers',
      name: 'Migration Blocker Analysis',
      description: 'Comprehensive analysis of migration challenges with AI-generated executive summary and detailed remediation plans for each blocker.',
      icon: <AlertTriangle className="h-5 w-5" />,
      color: 'text-red-600',
      bgColor: 'bg-red-100'
    },
    {
      type: 'executive-summary',
      name: 'Executive Summary',
      description: 'Business-focused summary with key insights, cost analysis, and strategic recommendations tailored for C-level executives.',
      icon: <BarChart3 className="h-5 w-5" />,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100'
    },
    {
      type: 'technical-analysis',
      name: 'Technical Implementation Guide',
      description: 'Detailed technical specifications, implementation steps, resource requirements, and technical considerations for migration teams.',
      icon: <Server className="h-5 w-5" />,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100'
    },
    {
      type: 'migration-roadmap',
      name: 'Migration Roadmap',
      description: 'AI-generated phased migration plan with timelines, dependencies, resource requirements, and risk mitigation strategies.',
      icon: <Calendar className="h-5 w-5" />,
      color: 'text-green-600',
      bgColor: 'bg-green-100'
    }
  ];

  const downloadReport = async (reportType: string, reportName: string) => {
    setDownloadingReport(reportType);
    setDownloadStatus(prev => ({ ...prev, [reportType]: null }));

    try {
      let blob: Blob;
      let filename: string;

      switch (reportType) {
        case 'migration-blockers':
          blob = await apiService.downloadMigrationBlockerReport(sessionId);
          filename = `migration_blocker_report_${sessionId}.pdf`;
          break;
        case 'executive-summary':
          blob = await apiService.downloadExecutiveSummaryReport(sessionId);
          filename = `executive_summary_${sessionId}.pdf`;
          break;
        case 'technical-analysis':
          blob = await apiService.downloadTechnicalAnalysisReport(sessionId);
          filename = `technical_analysis_${sessionId}.pdf`;
          break;
        case 'migration-roadmap':
          blob = await apiService.downloadMigrationRoadmapReport(sessionId);
          filename = `migration_roadmap_${sessionId}.pdf`;
          break;
        default:
          throw new Error(`Unknown report type: ${reportType}`);
      }

      // Download the file
      apiService.downloadBlobAsFile(blob, filename);
      
      setDownloadStatus(prev => ({ ...prev, [reportType]: 'success' }));
      
      // Clear success status after 3 seconds
      setTimeout(() => {
        setDownloadStatus(prev => ({ ...prev, [reportType]: null }));
      }, 3000);

    } catch (error) {
      console.error(`Failed to download ${reportName}:`, error);
      setDownloadStatus(prev => ({ ...prev, [reportType]: 'error' }));
      
      // Clear error status after 5 seconds
      setTimeout(() => {
        setDownloadStatus(prev => ({ ...prev, [reportType]: null }));
      }, 5000);
    } finally {
      setDownloadingReport(null);
    }
  };

  const getStatusIcon = (reportType: string) => {
    const status = downloadStatus[reportType];
    if (status === 'success') {
      return <CheckCircle className="h-4 w-4 text-green-600" />;
    } else if (status === 'error') {
      return <XCircle className="h-4 w-4 text-red-600" />;
    }
    return null;
  };

  const getStatusMessage = (reportType: string) => {
    const status = downloadStatus[reportType];
    if (status === 'success') {
      return <span className="text-sm text-green-600 ml-2">Downloaded successfully!</span>;
    } else if (status === 'error') {
      return <span className="text-sm text-red-600 ml-2">Download failed. Please try again.</span>;
    }
    return null;
  };

  return (
    <div className="card mb-8">
      <div className="card-header">
        <div className="flex items-center">
          <FileText className="h-6 w-6 text-primary-600 mr-3" />
          <h3 className="text-xl font-semibold text-gray-900">AI-Powered Reports</h3>
        </div>
        <p className="text-sm text-gray-600 mt-2">
          Download comprehensive PDF reports with AI-generated insights and recommendations
        </p>
      </div>
      
      {downloadingReport && (
        <div className="px-6 pb-4">
          <AIProcessingIndicator 
            isProcessing={true}
            message={`AI is generating your ${reportTypes.find(r => r.type === downloadingReport)?.name || 'report'}...`}
            progress={undefined}
          />
        </div>
      )}
      
      <div className="card-content">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {reportTypes.map((report) => (
            <div key={report.type} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
              <div className="flex items-center mb-3">
                <div className={`flex-shrink-0 w-10 h-10 ${report.bgColor} rounded-lg flex items-center justify-center`}>
                  <span className={report.color}>{report.icon}</span>
                </div>
                <div className="ml-3 flex-1">
                  <h4 className="text-lg font-medium text-gray-900">{report.name}</h4>
                  <div className="flex items-center">
                    {getStatusIcon(report.type)}
                    {getStatusMessage(report.type)}
                  </div>
                </div>
              </div>
              
              <p className="text-sm text-gray-600 mb-3 leading-relaxed">
                {report.description}
              </p>
              
              <div className="flex items-center justify-between mb-4">
                <AIBadge variant="info" size="sm" />
                <span className="text-xs text-gray-500">AI-Generated Content</span>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="text-xs text-gray-500">
                  <span className="inline-flex items-center">
                    <FileText className="h-3 w-3 mr-1" />
                    PDF Format
                  </span>
                </div>
                
                <button
                  onClick={() => downloadReport(report.type, report.name)}
                  disabled={downloadingReport === report.type}
                  className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white transition-colors ${
                    downloadingReport === report.type
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500'
                  }`}
                >
                  {downloadingReport === report.type ? (
                    <>
                      <Loader className="h-4 w-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Download className="h-4 w-4 mr-2" />
                      Download PDF
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
        
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <FileText className="h-5 w-5 text-blue-600 mt-0.5" />
            </div>
            <div className="ml-3">
              <h4 className="text-sm font-medium text-blue-900">About AI-Powered Reports</h4>
              <p className="text-sm text-blue-700 mt-1">
                These reports are generated using advanced AI analysis of your VMware environment. 
                Each report includes intelligent insights, detailed remediation plans, and business-focused 
                recommendations tailored to your specific migration requirements.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportDownloadSection;
