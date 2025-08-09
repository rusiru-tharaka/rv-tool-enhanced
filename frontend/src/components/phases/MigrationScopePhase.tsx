import React, { useState, useEffect } from 'react';
import { 
  AlertTriangle, 
  CheckCircle, 
  Info, 
  Search,
  Filter,
  Download,
  BarChart,
  Server,
  HardDrive,
  FileText,
  XCircle,
  CheckSquare,
  PieChart,
  BarChart2,
  Power
} from 'lucide-react';
import { useSession } from '../../contexts/SessionContext';
import { apiService } from '../../services/api';
import { MigrationBlockerSeverity, FilterOptions } from '../../types';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title } from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';
import { 
  AIBadge, 
  ConfidenceScore, 
  AIEnhancedSection, 
  AIProcessingIndicator,
  AIInsightCard,
  AIMetricsDisplay 
} from '../AIIndicators';

// Register ChartJS components
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title);

interface MigrationScopePhaseProps {
  sessionId: string;
}

const MigrationScopePhase: React.FC<MigrationScopePhaseProps> = ({ sessionId }) => {
  const { state, analyzeMigrationScope } = useSession();
  const [blockers, setBlockers] = useState<any[]>([]);
  const [outOfScopeItems, setOutOfScopeItems] = useState<any[]>([]);
  const [workloadClassifications, setWorkloadClassifications] = useState<any[]>([]);
  const [infrastructureInsights, setInfrastructureInsights] = useState<any>(null);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [analysisTriggered, setAnalysisTriggered] = useState(false); // Track if auto-analysis was triggered
  const [filters, setFilters] = useState<FilterOptions>({
    page: 1,
    page_size: 10,
    sort_by: 'severity',
    sort_order: 'desc'
  });

  // Calculate derived values
  const totalVMs = state.migrationScopeAnalysis?.total_vms || 0;
  const outOfScopeCount = state.migrationScopeAnalysis?.out_of_scope_items?.length || 0;
  const inScopeCount = totalVMs - outOfScopeCount;

  // Load data from state when analysis is available, or auto-trigger if needed
  useEffect(() => {
    console.log('🔄 [Migration Scope] useEffect triggered, checking state...');
    console.log('🔄 [Migration Scope] state.migrationScopeAnalysis exists:', !!state.migrationScopeAnalysis);
    console.log('🔄 [Migration Scope] analysisTriggered:', analysisTriggered);
    
    if (state.migrationScopeAnalysis) {
      console.log('📊 [Migration Scope] Loading data from state...');
      console.log('📊 [Migration Scope] Full Analysis Data:', state.migrationScopeAnalysis);
      
      // Use data from state instead of making API calls
      const blockers = state.migrationScopeAnalysis.migration_blockers || [];
      const outOfScopeItems = state.migrationScopeAnalysis.out_of_scope_items || [];
      const workloadClassifications = state.migrationScopeAnalysis.workload_classifications || [];
      const infrastructureInsights = state.migrationScopeAnalysis.infrastructure_insights || null;
      
      console.log('🚫 [Migration Scope] Migration Blockers Count:', blockers.length);
      console.log('❌ [Migration Scope] Out-of-Scope Items Count:', outOfScopeItems.length);
      console.log('📋 [Migration Scope] Workload Classifications Count:', workloadClassifications.length);
      
      if (outOfScopeItems.length > 0) {
        console.log('❌ [Migration Scope] Out-of-Scope VMs Details:');
        outOfScopeItems.forEach((item: any, index: number) => {
          console.log(`   ${index + 1}. ${item.vm_name} - ${item.reason} (${item.category})`);
        });
      } else {
        console.log('✅ [Migration Scope] No out-of-scope VMs found');
      }
      
      setBlockers(blockers);
      setOutOfScopeItems(outOfScopeItems);
      setWorkloadClassifications(workloadClassifications);
      setInfrastructureInsights(infrastructureInsights);
      
      const summary = {
        total_vms: state.migrationScopeAnalysis.total_vms,
        estimated_timeline_months: state.migrationScopeAnalysis.estimated_timeline_months,
        complexity_score: state.migrationScopeAnalysis.complexity_score
      };
      
      console.log('📊 [Migration Scope] Summary Data:', summary);
      console.log('📊 [Migration Scope] Total VMs:', summary.total_vms);
      console.log('📊 [Migration Scope] In-Scope VMs:', summary.total_vms - outOfScopeItems.length);
      
      setSummary(summary);
    } else if (!analysisTriggered && !loading && state.currentSession && state.currentSession.vm_inventory && state.currentSession.vm_inventory.length > 0) {
      console.log('🚀 [Migration Scope] No analysis data found, auto-triggering analysis...');
      console.log('📊 [Migration Scope] VM inventory available:', state.currentSession.vm_inventory.length, 'VMs');
      setAnalysisTriggered(true); // Prevent multiple triggers
      // Auto-trigger analysis if we have VM inventory but no analysis data
      handleAnalyze();
    } else if (!analysisTriggered && !loading) {
      console.log('ℹ️ [Migration Scope] Waiting for VM inventory or user action...');
    }
  }, [state.migrationScopeAnalysis, sessionId]); // Remove analysisTriggered from dependencies to prevent loops

  const handleAnalyze = async () => {
    console.log('🚀 [Migration Scope] Starting analysis for session:', sessionId);
    try {
      setLoading(true);
      await analyzeMigrationScope(sessionId);
      console.log('✅ [Migration Scope] Analysis completed successfully');
    } catch (error) {
      console.error('❌ [Migration Scope] Analysis failed:', error);
      // Reset trigger state on error so user can retry
      setAnalysisTriggered(false);
    } finally {
      setLoading(false);
    }
  };

  const loadMigrationScopeData = async () => {
    // This function is no longer needed since we use state data
    // But keeping it for compatibility
    if (state.migrationScopeAnalysis) {
      setBlockers(state.migrationScopeAnalysis.migration_blockers || []);
      setOutOfScopeItems(state.migrationScopeAnalysis.out_of_scope_items || []);
      setWorkloadClassifications(state.migrationScopeAnalysis.workload_classifications || []);
      setInfrastructureInsights(state.migrationScopeAnalysis.infrastructure_insights || null);
      setSummary({
        total_vms: state.migrationScopeAnalysis.total_vms,
        estimated_timeline_months: state.migrationScopeAnalysis.estimated_timeline_months,
        complexity_score: state.migrationScopeAnalysis.complexity_score
      });
    }
  };

  const getSeverityIcon = (severity: MigrationBlockerSeverity) => {
    switch (severity) {
      case MigrationBlockerSeverity.CRITICAL:
        return <AlertTriangle className="h-4 w-4 text-danger-500" />;
      case MigrationBlockerSeverity.HIGH:
        return <AlertTriangle className="h-4 w-4 text-warning-500" />;
      case MigrationBlockerSeverity.MEDIUM:
        return <Info className="h-4 w-4 text-primary-500" />;
      case MigrationBlockerSeverity.LOW:
        return <CheckCircle className="h-4 w-4 text-success-500" />;
      default:
        return <Info className="h-4 w-4 text-gray-500" />;
    }
  };

  const getSeverityBadgeClass = (severity: MigrationBlockerSeverity) => {
    switch (severity) {
      case MigrationBlockerSeverity.CRITICAL:
        return 'badge-danger';
      case MigrationBlockerSeverity.HIGH:
        return 'badge-warning';
      case MigrationBlockerSeverity.MEDIUM:
        return 'badge-info';
      case MigrationBlockerSeverity.LOW:
        return 'badge-success';
      default:
        return 'badge-info';
    }
  };

  const handleExport = async () => {
    try {
      const exportData = await apiService.exportMigrationScope(sessionId, 'json');
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `migration-scope-${sessionId.slice(0, 8)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
    }
  };

  const handleExportOutOfScope = () => {
    try {
      // Convert out of scope items to CSV format
      const headers = ['VM Name', 'Category', 'Reason', 'Auto Detected'];
      const csvRows = [
        headers.join(','),
        ...outOfScopeItems.map(item => [
          `"${item.vm_name || ''}"`,
          `"${item.category?.replace(/_/g, ' ') || 'Other'}"`,
          `"${(item.reason || '').replace(/"/g, '""')}"`,
          item.auto_detected ? 'Yes' : 'No'
        ].join(','))
      ];
      
      const csvContent = csvRows.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `out-of-scope-vms-${sessionId.slice(0, 8)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('CSV export failed:', error);
    }
  };

  // Group out of scope items by category and count them
  const outOfScopeByCategory = outOfScopeItems.reduce((acc, item) => {
    // Format the category name for better readability
    let category = item.category || 'other';
    
    // Convert vmware_management to "VMware management Servers"
    if (category.includes('vmware') && category.includes('management')) {
      category = 'VMware management Servers';
    }
    // Convert containerization to "VMware containerization platform"
    else if (category.includes('container')) {
      category = 'VMware containerization platform';
    }
    // For other categories, just format them nicely
    else {
      category = category.replace(/_/g, ' ') + ' Servers';
    }
    
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(item);
    return acc;
  }, {});

  // Create a summary of out of scope items by category
  const outOfScopeSummary = Object.entries(outOfScopeByCategory).map(([category, items]) => ({
    category: category,
    count: Array.isArray(items) ? items.length : 0
  }));

  // Prepare chart data for OS breakdown
  const osBreakdownData = {
    labels: infrastructureInsights?.os_breakdown ? Object.keys(infrastructureInsights.os_breakdown).map(os => os.charAt(0).toUpperCase() + os.slice(1)) : [],
    datasets: [
      {
        data: infrastructureInsights?.os_breakdown ? Object.values(infrastructureInsights.os_breakdown) : [],
        backgroundColor: [
          'rgba(54, 162, 235, 0.6)',  // Blue for Windows
          'rgba(255, 99, 132, 0.6)',  // Red for Linux
          'rgba(255, 206, 86, 0.6)',  // Yellow for Other
        ],
        borderColor: [
          'rgba(54, 162, 235, 1)',
          'rgba(255, 99, 132, 1)',
          'rgba(255, 206, 86, 1)',
        ],
        borderWidth: 1,
      },
    ],
  };

  // Prepare chart data for Production vs Non-Production
  const prodNonProdData = {
    labels: infrastructureInsights?.prod_nonprod_ratio ? Object.keys(infrastructureInsights.prod_nonprod_ratio).map(env => env.charAt(0).toUpperCase() + env.slice(1)) : [],
    datasets: [
      {
        label: 'Server Count',
        data: infrastructureInsights?.prod_nonprod_ratio ? Object.values(infrastructureInsights.prod_nonprod_ratio) : [],
        backgroundColor: [
          'rgba(75, 192, 192, 0.6)',  // Green for Production
          'rgba(153, 102, 255, 0.6)', // Purple for Non-Production
        ],
      },
    ],
  };

  // Calculate power state data
  const powerStateCount = {
    poweredOn: 0,
    poweredOff: 0
  };

  if (state.currentSession?.vm_inventory) {
    state.currentSession.vm_inventory.forEach(vm => {
      if (vm.power_state?.toLowerCase().includes('off') || 
          vm.power_state?.toLowerCase().includes('suspend')) {
        powerStateCount.poweredOff++;
      } else {
        powerStateCount.poweredOn++;
      }
    });
  }

  // Prepare chart data for Power State
  const powerStateData = {
    labels: ['Powered On', 'Powered Off'],
    datasets: [
      {
        data: [powerStateCount.poweredOn, powerStateCount.poweredOff],
        backgroundColor: [
          'rgba(75, 192, 192, 0.6)',  // Green for Powered On
          'rgba(255, 99, 132, 0.6)',  // Red for Powered Off
        ],
        borderColor: [
          'rgba(75, 192, 192, 1)',
          'rgba(255, 99, 132, 1)',
        ],
        borderWidth: 1,
      },
    ],
  };

  // Prepare chart data for Total Storage
  const totalStorageData = {
    labels: ['Total Storage (TB)'],
    datasets: [
      {
        label: 'Storage (TB)',
        data: [infrastructureInsights?.total_storage_tb || 0],
        backgroundColor: 'rgba(54, 162, 235, 0.6)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
      },
    ],
  };

  // Chart options with data labels
  const pieOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.label || '';
            const value = context.raw || 0;
            const total = context.dataset.data.reduce((a, b) => a + b, 0);
            const percentage = Math.round((value / total) * 100);
            return `${label}: ${value} (${percentage}%)`;
          }
        }
      },
      datalabels: {
        formatter: (value, ctx) => {
          const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
          const percentage = Math.round((value / total) * 100);
          return percentage + '%';
        },
        color: '#fff',
        font: {
          weight: 'bold',
          size: 12
        }
      }
    }
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true
      }
    },
    plugins: {
      datalabels: {
        anchor: 'end',
        align: 'top',
        formatter: (value) => value,
        color: '#333',
        font: {
          weight: 'bold'
        }
      }
    }
  };

  if (!state.migrationScopeAnalysis) {
    return (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Migration Scope Analysis
        </h3>
        <p className="text-gray-600 mb-6">
          Analyze your VM inventory to identify migration blockers and classify workloads
        </p>
        <button
          onClick={handleAnalyze}
          disabled={state.loading.isLoading}
          className="btn-primary"
        >
          {state.loading.isLoading ? 'Analyzing...' : 'Start Analysis'}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="card-content">
            <div className="flex items-center">
              <Server className="h-8 w-8 text-primary-600" />
              <div className="ml-4">
                <p className="text-2xl font-semibold text-gray-900">
                  {state.migrationScopeAnalysis.total_vms}
                </p>
                <p className="text-sm text-gray-600">Total VMs</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content">
            <div className="flex items-center">
              <AlertTriangle className="h-8 w-8 text-warning-600" />
              <div className="ml-4">
                <p className="text-2xl font-semibold text-gray-900">
                  {state.migrationScopeAnalysis.migration_blockers.length}
                </p>
                <p className="text-sm text-gray-600">Blockers Found</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content">
            <div className="flex items-center">
              <BarChart className="h-8 w-8 text-success-600" />
              <div className="ml-4">
                <p className="text-2xl font-semibold text-gray-900">
                  {state.migrationScopeAnalysis.complexity_score}
                </p>
                <p className="text-sm text-gray-600">Complexity Score</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content">
            <div className="flex items-center">
              <HardDrive className="h-8 w-8 text-info-600" />
              <div className="ml-4">
                <p className="text-2xl font-semibold text-gray-900">
                  {state.migrationScopeAnalysis.estimated_timeline_months}
                </p>
                <p className="text-sm text-gray-600">Est. Months</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AI Analysis Metrics */}
      <AIMetricsDisplay 
        metrics={{
          totalAnalyzed: state.migrationScopeAnalysis?.total_vms || 0,
          aiConfidence: state.migrationScopeAnalysis?.ai_metadata?.confidence || 0.8,
          insightsGenerated: (state.migrationScopeAnalysis?.migration_blockers?.length || 0) + 
                           (state.migrationScopeAnalysis?.workload_classifications?.length || 0),
          recommendationsCount: state.migrationScopeAnalysis?.migration_blockers?.length || 0
        }}
        className="mb-6"
      />

      {/* AI-Enhanced Migration Blockers */}
      <AIEnhancedSection 
        title="Migration Blockers" 
        variant="analysis"
        confidence={state.migrationScopeAnalysis?.ai_metadata?.confidence || 0.8}
        className="mb-6"
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <AIBadge variant="primary" size="sm" />
            <span className="text-sm text-gray-600">
              AI-powered blocker detection with intelligent remediation suggestions
            </span>
          </div>
          <button onClick={handleExport} className="btn-outline">
            <Download className="h-4 w-4 mr-2" />
            Export
          </button>
        </div>
        
        {blockers.length > 0 ? (
          <div className="space-y-4">
            {blockers.map((blocker, index) => (
              <AIInsightCard
                key={index}
                title={blocker.vm_name}
                insight={blocker.description}
                confidence={blocker.ai_confidence || 0.8}
                actionable={true}
                priority={blocker.severity === 'critical' ? 'high' : blocker.severity === 'high' ? 'medium' : 'low'}
                className="mb-4"
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <CheckCircle className="h-12 w-12 text-success-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No migration blockers found!</p>
            <AIBadge variant="success" size="sm" />
          </div>
        )}
      </AIEnhancedSection>

      {/* Out of Scope Section - Modified to show only summary by category with download option */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">Out of Scope</h3>
            <div className="flex items-center space-x-2">
              <div className="text-sm text-gray-500">
                {outOfScopeCount} VMs ({totalVMs > 0 ? ((outOfScopeCount / totalVMs) * 100).toFixed(1) : 0}% of total)
              </div>
              <button 
                onClick={handleExportOutOfScope} 
                className="btn-outline btn-sm"
                disabled={outOfScopeItems.length === 0}
              >
                <Download className="h-3 w-3 mr-1" />
                Export CSV
              </button>
            </div>
          </div>
        </div>
        <div className="card-content">
          {outOfScopeItems.length > 0 ? (
            <div>
              {/* Summary by category - Updated format */}
              <div className="space-y-2">
                {outOfScopeSummary.map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded-md">
                    <div className="flex items-center">
                      <XCircle className="h-4 w-4 text-danger-500 mr-2" />
                      <span className="text-sm font-medium text-gray-900">
                        {item.count} : {item.category.split(' ').map(word => 
                          word.charAt(0).toUpperCase() + word.slice(1)
                        ).join(' ')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <CheckCircle className="h-12 w-12 text-success-400 mx-auto mb-4" />
              <p className="text-gray-600">No out of scope items found!</p>
            </div>
          )}
        </div>
      </div>

      {/* Workload Classifications */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Workload Classifications</h3>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* In-Scope Servers tile */}
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="flex items-center justify-center mb-2">
                <CheckSquare className="h-6 w-6 text-blue-500 mr-2" />
                <p className="text-2xl font-semibold text-gray-900">{inScopeCount}</p>
              </div>
              <p className="text-sm text-gray-600">In-Scope Servers</p>
              <p className="text-xs text-gray-500">
                {totalVMs > 0 ? ((inScopeCount / totalVMs) * 100).toFixed(1) : 0}% of total
              </p>
            </div>

            {/* Existing workload classifications */}
            {state.migrationScopeAnalysis.workload_classifications.map((classification, index) => (
              <div key={index} className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-2xl font-semibold text-gray-900">
                  {classification.vm_count}
                </p>
                <p className="text-sm text-gray-600 capitalize">
                  {classification.classification}
                </p>
                <p className="text-xs text-gray-500">
                  {classification.percentage.toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Infrastructure Insights - Updated with charts with data labels */}
      {infrastructureInsights && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">
              Infrastructure Insights <span className="text-sm text-gray-500">(In-Scope Servers Only)</span>
            </h3>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* OS Breakdown Pie Chart */}
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                  <PieChart className="h-4 w-4 mr-2 text-primary-600" />
                  OS Breakdown
                </h4>
                <div className="h-64">
                  <Pie 
                    data={osBreakdownData} 
                    options={{
                      ...pieOptions,
                      plugins: {
                        ...pieOptions.plugins,
                        tooltip: {
                          ...pieOptions.plugins.tooltip,
                          callbacks: {
                            label: function(context) {
                              const label = context.label || '';
                              const value = context.raw || 0;
                              const total = context.dataset.data.reduce((a, b) => a + b, 0);
                              const percentage = Math.round((value / total) * 100);
                              return `${label}: ${value} (${percentage}%)`;
                            }
                          }
                        }
                      }
                    }}
                    plugins={[{
                      id: 'datalabels',
                      afterDatasetsDraw(chart) {
                        const {ctx, data} = chart;
                        ctx.save();
                        const total = data.datasets[0].data.reduce((sum, value) => sum + value, 0);
                        
                        chart._metasets[0].data.forEach((datapoint, i) => {
                          const {x, y} = datapoint.tooltipPosition();
                          const value = data.datasets[0].data[i];
                          const percentage = Math.round((value / total) * 100);
                          
                          // Show label for all segments
                          ctx.fillStyle = '#fff';
                          ctx.font = 'bold 12px Arial';
                          ctx.textAlign = 'center';
                          ctx.textBaseline = 'middle';
                          ctx.fillText(`${percentage}%`, x, y);
                        });
                        ctx.restore();
                      }
                    }]}
                  />
                </div>
              </div>
              
              {/* Production vs Non-Production Bar Chart */}
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                  <BarChart2 className="h-4 w-4 mr-2 text-primary-600" />
                  Production vs Non-Production
                </h4>
                <div className="h-64">
                  <Bar 
                    data={prodNonProdData} 
                    options={{
                      ...barOptions,
                      plugins: {
                        ...barOptions.plugins,
                        tooltip: {
                          callbacks: {
                            label: function(context) {
                              const label = context.dataset.label || '';
                              const value = context.raw || 0;
                              const total = context.dataset.data.reduce((a, b) => a + b, 0);
                              const percentage = Math.round((value / total) * 100);
                              return `${label}: ${value} (${percentage}%)`;
                            }
                          }
                        }
                      }
                    }}
                    plugins={[{
                      id: 'datalabels',
                      afterDatasetsDraw(chart) {
                        const {ctx, data, chartArea: {top, bottom, left, right, width, height}} = chart;
                        ctx.save();
                        
                        const total = data.datasets[0].data.reduce((sum, value) => sum + value, 0);
                        
                        data.datasets[0].data.forEach((datapoint, i) => {
                          const meta = chart.getDatasetMeta(0);
                          const element = meta.data[i];
                          const {x, y} = element.tooltipPosition();
                          const percentage = Math.round((datapoint / total) * 100);
                          
                          ctx.fillStyle = '#333';
                          ctx.font = 'bold 12px Arial';
                          ctx.textAlign = 'center';
                          ctx.textBaseline = 'bottom';
                          ctx.fillText(`${datapoint} (${percentage}%)`, x, y - 5);
                        });
                        ctx.restore();
                      }
                    }]}
                  />
                </div>
              </div>
              
              {/* Power State Pie Chart */}
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                  <Power className="h-4 w-4 mr-2 text-primary-600" />
                  Power State
                </h4>
                <div className="h-64">
                  <Pie 
                    data={powerStateData} 
                    options={{
                      ...pieOptions,
                      plugins: {
                        ...pieOptions.plugins,
                        tooltip: {
                          ...pieOptions.plugins.tooltip,
                          callbacks: {
                            label: function(context) {
                              const label = context.label || '';
                              const value = context.raw || 0;
                              const total = context.dataset.data.reduce((a, b) => a + b, 0);
                              const percentage = Math.round((value / total) * 100);
                              return `${label}: ${value} (${percentage}%)`;
                            }
                          }
                        }
                      }
                    }}
                    plugins={[{
                      id: 'datalabels',
                      afterDatasetsDraw(chart) {
                        const {ctx, data} = chart;
                        ctx.save();
                        const total = data.datasets[0].data.reduce((sum, value) => sum + value, 0);
                        
                        chart._metasets[0].data.forEach((datapoint, i) => {
                          const {x, y} = datapoint.tooltipPosition();
                          const value = data.datasets[0].data[i];
                          const percentage = Math.round((value / total) * 100);
                          
                          // Show label for all segments
                          ctx.fillStyle = '#fff';
                          ctx.font = 'bold 12px Arial';
                          ctx.textAlign = 'center';
                          ctx.textBaseline = 'middle';
                          ctx.fillText(`${percentage}%`, x, y);
                        });
                        ctx.restore();
                      }
                    }]}
                  />
                </div>
              </div>
              
              {/* Total Storage Bar Chart */}
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3 flex items-center">
                  <HardDrive className="h-4 w-4 mr-2 text-primary-600" />
                  Total Storage
                </h4>
                <div className="h-64">
                  <Bar 
                    data={totalStorageData} 
                    options={{
                      ...barOptions,
                      plugins: {
                        ...barOptions.plugins,
                        tooltip: {
                          callbacks: {
                            label: function(context) {
                              const label = context.dataset.label || '';
                              const value = context.raw || 0;
                              return `${label}: ${value.toFixed(1)} TB`;
                            }
                          }
                        }
                      }
                    }}
                    plugins={[{
                      id: 'datalabels',
                      afterDatasetsDraw(chart) {
                        const {ctx, data} = chart;
                        ctx.save();
                        
                        data.datasets[0].data.forEach((datapoint, i) => {
                          const meta = chart.getDatasetMeta(0);
                          const element = meta.data[i];
                          const {x, y} = element.tooltipPosition();
                          
                          ctx.fillStyle = '#333';
                          ctx.font = 'bold 12px Arial';
                          ctx.textAlign = 'center';
                          ctx.textBaseline = 'bottom';
                          ctx.fillText(`${datapoint.toFixed(1)} TB`, x, y - 5);
                        });
                        ctx.restore();
                      }
                    }]}
                  />
                </div>
              </div>
            </div>
            <div className="mt-4 p-3 bg-blue-50 rounded-md">
              <p className="text-sm text-blue-800">
                <Info className="h-4 w-4 inline-block mr-1" />
                These statistics reflect only the {inScopeCount} in-scope servers that will be migrated to AWS.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MigrationScopePhase;
