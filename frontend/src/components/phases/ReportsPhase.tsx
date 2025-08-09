import React, { useRef } from 'react';
import { 
  FileText, 
  Download, 
  BarChart3, 
  TrendingUp,
  TrendingDown,
  Server, 
  Cloud, 
  DollarSign,
  Calendar,
  Users,
  Database,
  Shield,
  Zap,
  XCircle
} from 'lucide-react';
import { useSession } from '../../contexts/SessionContext';
import generateTCOReportPDF from '../../utils/pdfGenerator';
import ReportDownloadSection from '../ReportDownloadSection';
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  BarElement, 
  Title, 
  Tooltip, 
  Legend,
  ArcElement,
  PointElement,
  LineElement
} from 'chart.js';
import { Bar, Pie, Line } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  CategoryScale, 
  LinearScale, 
  BarElement, 
  Title, 
  Tooltip, 
  Legend,
  ArcElement,
  PointElement,
  LineElement
);

interface ReportsPhaseProps {
  sessionId: string;
}

const ReportsPhase: React.FC<ReportsPhaseProps> = ({ sessionId }) => {
  const { state } = useSession();
  const reportRef = useRef<HTMLDivElement>(null);

  const handleDownloadPDF = () => {
    const reportData = {
      totalVMs: state.migrationScopeAnalysis?.total_vms || 0,
      monthlyCost: state.costEstimatesAnalysis?.cost_summary?.total_monthly_cost || 0,
      annualCost: state.costEstimatesAnalysis?.cost_summary?.total_annual_cost || 0,
      infrastructureCost: state.costEstimatesAnalysis?.cost_summary?.infrastructure_monthly_cost || 0,
      networkCost: state.costEstimatesAnalysis?.cost_summary?.network_monthly_cost || 0,
      observabilityCost: state.costEstimatesAnalysis?.cost_summary?.observability_monthly_cost || 0,
      modernizationOpportunities: state.modernizationAnalysis?.total_opportunities || 0,
    };
    
    generateTCOReportPDF(reportData, sessionId);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  // Helper function to export VM estimates to CSV
  const exportToCSV = (estimates: any[]) => {
    if (!estimates || estimates.length === 0) return;
    
    // Define CSV headers
    const headers = [
      'VM Name',
      'CPU Cores',
      'Memory (GB)',
      'Storage (GB)',
      'Recommended Instance Type',
      'Instance Cost ($)',
      'Storage Cost ($)',
      'Total Monthly Cost ($)',
      'Pricing Plan',
      'Environment'
    ];
    
    // Convert estimates to CSV rows
    const rows = estimates.map(estimate => {
      // Calculate storage cost (approximate $0.10 per GB per month)
      const storageGB = estimate.current_storage_gb || 0;
      const storageCost = storageGB * 0.10;
      const instanceCost = estimate.projected_monthly_cost - storageCost;
      
      // Determine if production or non-production
      const isProd = estimate.vm_name.toLowerCase().includes('prod') || 
                    estimate.vm_name.toLowerCase().includes('prd');
      const environment = isProd ? 'Production' : 'Non-Production';
      
      return [
        estimate.vm_name || 'Unknown',
        estimate.current_cpu || 0,
        estimate.current_memory_gb || 0,
        storageGB,
        estimate.recommended_instance_type || 'Unknown',
        instanceCost.toFixed(2),
        storageCost.toFixed(2),
        (estimate.projected_monthly_cost || 0).toFixed(2),
        estimate.pricing_plan || 'On-Demand',
        environment
      ];
    });
    
    // Combine headers and rows
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => {
        // Handle cells that might contain commas by wrapping in quotes
        const cellStr = String(cell);
        return cellStr.includes(',') ? `"${cellStr}"` : cellStr;
      }).join(','))
    ].join('\n');
    
    // Create a Blob and download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `vm-cost-estimates-${sessionId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  // Calculate summary data from all phases
  const totalVMs = state.migrationScopeAnalysis?.total_vms || 0;
  const migrationBlockers = state.migrationScopeAnalysis?.migration_blockers?.length || 0;
  const monthlyCost = state.costEstimatesAnalysis?.cost_summary?.total_monthly_cost || 0;
  const annualCost = state.costEstimatesAnalysis?.cost_summary?.total_annual_cost || 0;
  const modernizationOpportunities = state.modernizationAnalysis?.total_opportunities || 0;
  
  // Get out-of-scope items
  const outOfScopeItems = state.migrationScopeAnalysis?.out_of_scope_items || [];
  const outOfScopeCount = outOfScopeItems.length || 0;
  
  // Group modernization opportunities by category
  const modernizationByCategory = React.useMemo(() => {
    const opportunities = state.modernizationAnalysis?.modernization_opportunities || [];
    const categories: Record<string, { count: number, savings: number }> = {};
    
    opportunities.forEach(opportunity => {
      const category = opportunity.modernization_type || 'unknown';
      if (!categories[category]) {
        categories[category] = { count: 0, savings: 0 };
      }
      categories[category].count += 1;
      categories[category].savings += opportunity.monthly_savings || 0;
    });
    
    return Object.entries(categories).map(([category, data]) => ({
      category: category.replace(/_/g, ' '),
      count: data.count,
      savings: data.savings
    }));
  }, [state.modernizationAnalysis?.modernization_opportunities]);
  
  // Sort detailed estimates by total cost (highest to lowest)
  const sortedEstimates = React.useMemo(() => {
    const estimates = state.costEstimatesAnalysis?.detailed_estimates || [];
    return [...estimates].sort((a, b) => 
      (b.projected_monthly_cost || 0) - (a.projected_monthly_cost || 0)
    );
  }, [state.costEstimatesAnalysis?.detailed_estimates]);
  
  // Calculate "What If" modernization data for 5-year projection
  const whatIfData = React.useMemo(() => {
    const monthlySavings = state.modernizationAnalysis?.summary?.total_monthly_savings || 0;
    const annualSavings = monthlySavings * 12;
    
    // Base TCO for 5 years (without modernization)
    const baseTCO = state.costEstimatesAnalysis?.cost_summary?.yearly_tco || [];
    
    // Calculate TCO with modernization after 2 years
    const modernizedTCO = baseTCO.map((yearCost, index) => {
      // No savings in years 1-2, apply savings in years 3-5
      return index < 2 ? yearCost : yearCost - annualSavings;
    });
    
    return {
      labels: ['Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5'],
      baseTCO,
      modernizedTCO
    };
  }, [
    state.costEstimatesAnalysis?.cost_summary?.yearly_tco,
    state.modernizationAnalysis?.summary?.total_monthly_savings
  ]);

  return (
    <div className="space-y-6">
      {/* Report Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">VMware to AWS Migration TCO Report</h2>
          <p className="text-gray-600">Comprehensive analysis and cost optimization recommendations</p>
        </div>
        <button
          onClick={handleDownloadPDF}
          className="btn-primary flex items-center"
        >
          <Download className="h-4 w-4 mr-2" />
          Download PDF
        </button>
      </div>

      {/* Report Content */}
      <div ref={reportRef} className="bg-white">
        {/* Executive Summary */}
        <div className="card mb-8">
          <div className="card-header bg-primary-50">
            <div className="flex items-center">
              <FileText className="h-6 w-6 text-primary-600 mr-3" />
              <h3 className="text-xl font-semibold text-gray-900">Executive Summary</h3>
            </div>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div className="text-center">
                <div className="flex items-center justify-center w-12 h-12 bg-blue-100 rounded-lg mx-auto mb-2">
                  <Server className="h-6 w-6 text-blue-600" />
                </div>
                <p className="text-2xl font-bold text-gray-900">{totalVMs}</p>
                <p className="text-sm text-gray-600">Total VMs Analyzed</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center w-12 h-12 bg-green-100 rounded-lg mx-auto mb-2">
                  <DollarSign className="h-6 w-6 text-green-600" />
                </div>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(monthlyCost)}</p>
                <p className="text-sm text-gray-600">Monthly AWS Cost</p>
              </div>
              <div className="text-center">
                <div className="flex items-center justify-center w-12 h-12 bg-purple-100 rounded-lg mx-auto mb-2">
                  <Zap className="h-6 w-6 text-purple-600" />
                </div>
                <p className="text-2xl font-bold text-gray-900">{modernizationOpportunities}</p>
                <p className="text-sm text-gray-600">Modernization Opportunities</p>
              </div>
            </div>
            
            <div className="prose max-w-none">
              <p className="text-gray-700 leading-relaxed">
                This comprehensive Total Cost of Ownership (TCO) analysis evaluates the migration of <strong>{totalVMs} virtual machines</strong> from 
                your current VMware infrastructure to Amazon Web Services (AWS). Our analysis identifies an estimated monthly cost of <strong>{formatCurrency(monthlyCost)}</strong> 
                for AWS infrastructure, with significant optimization opportunities through modernization initiatives.
              </p>
              <p className="text-gray-700 leading-relaxed mt-4">
                The migration assessment reveals <strong>{migrationBlockers} critical blockers</strong> that require attention, along with <strong>{modernizationOpportunities} modernization opportunities</strong> 
                including containerization, serverless computing, and managed services adoption.
              </p>
            </div>
          </div>
        </div>

        {/* Migration Scope Analysis */}
        <div className="card mb-8">
          <div className="card-header bg-blue-50">
            <h3 className="text-xl font-semibold text-gray-900">Migration Scope Analysis</h3>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Infrastructure Overview */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Infrastructure Overview</h4>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Virtual Machines</span>
                    <span className="font-medium">{totalVMs}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Estimated Timeline</span>
                    <span className="font-medium">{state.migrationScopeAnalysis?.estimated_timeline_months || 12} months</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Complexity Score</span>
                    <span className="font-medium">{state.migrationScopeAnalysis?.complexity_score || 75}/100</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Migration Blockers</span>
                    <span className="font-medium text-red-600">{migrationBlockers}</span>
                  </div>
                </div>
              </div>

              {/* Workload Classification */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Workload Classification</h4>
                <div className="space-y-3">
                  {state.migrationScopeAnalysis?.workload_classifications?.map((classification, index) => (
                    <div key={index} className="flex justify-between items-center">
                      <span className="text-gray-600 capitalize">{classification.classification}</span>
                      <div className="flex items-center">
                        <span className="font-medium mr-2">{classification.vm_count} VMs</span>
                        <span className="text-sm text-gray-500">({classification.percentage.toFixed(1)}%)</span>
                      </div>
                    </div>
                  )) || []}
                </div>
              </div>
            </div>

            {/* Migration Blockers */}
            {state.migrationScopeAnalysis?.migration_blockers && state.migrationScopeAnalysis.migration_blockers.length > 0 && (
              <div className="mt-8">
                <h4 className="text-lg font-medium text-gray-900 mb-4">Critical Migration Blockers</h4>
                <div className="space-y-4">
                  {state.migrationScopeAnalysis.migration_blockers.slice(0, 5).map((blocker, index) => (
                    <div key={index} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center mb-2">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mr-3 ${
                              blocker.severity === 'high' ? 'bg-red-100 text-red-800' :
                              blocker.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-green-100 text-green-800'
                            }`}>
                              {blocker.severity.toUpperCase()}
                            </span>
                            <h5 className="font-medium text-gray-900">{blocker.vm_name}</h5>
                          </div>
                          <p className="text-sm text-gray-600 mb-2">{blocker.description}</p>
                          <p className="text-sm text-blue-600"><strong>Remediation:</strong> {blocker.remediation}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Out of Scope Section */}
            {outOfScopeItems.length > 0 && (
              <div className="mt-8">
                <h4 className="text-lg font-medium text-gray-900 mb-4">Out of Scope</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-600">Total Out of Scope VMs</span>
                    <span className="font-medium">{outOfScopeCount} VMs ({totalVMs > 0 ? ((outOfScopeCount / totalVMs) * 100).toFixed(1) : 0}% of total)</span>
                  </div>
                  
                  {/* Group out-of-scope items by category */}
                  {Object.entries(outOfScopeItems.reduce((acc: Record<string, any[]>, item) => {
                    const category = item.reason || 'Other';
                    if (!acc[category]) acc[category] = [];
                    acc[category].push(item);
                    return acc;
                  }, {})).map(([category, items], index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded-md">
                      <div className="flex items-center">
                        <XCircle className="h-4 w-4 text-red-500 mr-2" />
                        <span className="text-sm font-medium text-gray-900">
                          {items.length} : {category.split(' ').map(word => 
                            word.charAt(0).toUpperCase() + word.slice(1)
                          ).join(' ')}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        {/* Cost Analysis */}
        <div className="card mb-8">
          <div className="card-header bg-green-50">
            <h3 className="text-xl font-semibold text-gray-900">AWS Cost Analysis</h3>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Cost Summary */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Cost Summary</h4>
                <div className="space-y-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-600">Infrastructure</span>
                      <span className="font-medium">{formatCurrency(state.costEstimatesAnalysis?.cost_summary?.infrastructure_monthly_cost || 0)}</span>
                    </div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-600">Network & Data Transfer</span>
                      <span className="font-medium">{formatCurrency(state.costEstimatesAnalysis?.cost_summary?.network_monthly_cost || 0)}</span>
                    </div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-gray-600">Monitoring & Backup</span>
                      <span className="font-medium">{formatCurrency(state.costEstimatesAnalysis?.cost_summary?.observability_monthly_cost || 0)}</span>
                    </div>
                    <div className="border-t pt-2 mt-2">
                      <div className="flex justify-between items-center font-semibold text-lg">
                        <span className="text-gray-900">Total Monthly</span>
                        <span className="text-gray-900">{formatCurrency(monthlyCost)}</span>
                      </div>
                      <div className="flex justify-between items-center font-semibold text-lg text-blue-600">
                        <span>Total Annual</span>
                        <span>{formatCurrency(annualCost)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* TCO Parameters */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">TCO Parameters</h4>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Target Region</span>
                    <span className="font-medium">{state.costEstimatesAnalysis?.tco_parameters?.target_region || 'us-east-1'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Pricing Model</span>
                    <span className="font-medium capitalize">{state.costEstimatesAnalysis?.tco_parameters?.pricing_model || 'on_demand'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Instance Family</span>
                    <span className="font-medium capitalize">{state.costEstimatesAnalysis?.tco_parameters?.instance_family || 'general_purpose'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Reserved Instance Term</span>
                    <span className="font-medium">{state.costEstimatesAnalysis?.tco_parameters?.reserved_instance_term || 'none'}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Cost Breakdown and 5-Year TCO Projection Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
              {/* Cost Breakdown */}
              <div className="card">
                <div className="card-header">
                  <h4 className="text-lg font-medium text-gray-900">Cost Breakdown</h4>
                </div>
                <div className="card-content">
                  <div className="h-64">
                    {state.costEstimatesAnalysis?.cost_summary && (
                      <Pie
                        data={{
                          labels: ['Infrastructure', 'Network', 'Observability'],
                          datasets: [
                            {
                              data: [
                                state.costEstimatesAnalysis.cost_summary.infrastructure_monthly_cost || 0,
                                state.costEstimatesAnalysis.cost_summary.network_monthly_cost || 0,
                                state.costEstimatesAnalysis.cost_summary.observability_monthly_cost || 0
                              ],
                              backgroundColor: [
                                'rgba(54, 162, 235, 0.6)',
                                'rgba(255, 206, 86, 0.6)',
                                'rgba(75, 192, 192, 0.6)'
                              ],
                              borderColor: [
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 206, 86, 1)',
                                'rgba(75, 192, 192, 1)'
                              ],
                              borderWidth: 1
                            }
                          ]
                        }}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: {
                              position: 'bottom'
                            },
                            tooltip: {
                              callbacks: {
                                label: function(context) {
                                  const label = context.label || '';
                                  const value = context.raw as number;
                                  const total = (context.dataset.data as number[]).reduce((a, b) => a + b, 0);
                                  const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                  return `${label}: ${formatCurrency(value)} (${percentage}%)`;
                                }
                              }
                            }
                          }
                        }}
                      />
                    )}
                  </div>
                </div>
              </div>

              {/* 5-Year TCO Projection */}
              <div className="card">
                <div className="card-header">
                  <h4 className="text-lg font-medium text-gray-900">5-Year TCO Projection</h4>
                  <p className="text-xs text-gray-600 mt-1">10% increase each year after the first year</p>
                </div>
                <div className="card-content">
                  <div className="h-64">
                    {state.costEstimatesAnalysis?.cost_summary?.yearly_tco && Array.isArray(state.costEstimatesAnalysis.cost_summary.yearly_tco) && state.costEstimatesAnalysis.cost_summary.yearly_tco.length > 0 ? (
                      <Line
                        data={{
                          labels: ['Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5'],
                          datasets: [
                            {
                              label: 'Annual Cost',
                              data: state.costEstimatesAnalysis.cost_summary.yearly_tco,
                              borderColor: 'rgb(59, 130, 246)',
                              backgroundColor: 'rgba(59, 130, 246, 0.5)',
                              tension: 0.1,
                              pointRadius: 5,
                              pointHoverRadius: 7,
                            },
                          ],
                        }}
                        options={{
                          responsive: true,
                          maintainAspectRatio: false,
                          plugins: {
                            legend: {
                              position: 'top',
                            },
                            tooltip: {
                              callbacks: {
                                label: function(context) {
                                  let label = context.dataset.label || '';
                                  if (label) {
                                    label += ': ';
                                  }
                                  if (context.parsed.y !== null) {
                                    label += '$' + context.parsed.y.toLocaleString(undefined, {maximumFractionDigits: 2});
                                  }
                                  return label;
                                }
                              }
                            }
                          },
                          scales: {
                            y: {
                              beginAtZero: true,
                              ticks: {
                                callback: function(value) {
                                  return '$' + value.toLocaleString();
                                }
                              }
                            }
                          }
                        }}
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <p className="text-gray-500">No data available for 5-year TCO projection</p>
                      </div>
                    )}
                  </div>
                  <div className="border-t pt-2 mt-4">
                    <div className="flex justify-between items-center font-medium">
                      <span className="text-gray-900">5-Year Total</span>
                      <span className="text-primary-600">
                        ${(state.costEstimatesAnalysis?.cost_summary?.five_year_tco || 0).toLocaleString(undefined, {maximumFractionDigits: 2})}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Analysis Summary (replacing Top VM Cost Estimates) */}
            <div className="mt-8">
              <div className="flex justify-between items-center mb-4">
                <h4 className="text-lg font-medium text-gray-900">Analysis Summary</h4>
                <button
                  onClick={() => exportToCSV(state.costEstimatesAnalysis?.detailed_estimates || [])}
                  className="btn-secondary text-sm"
                >
                  <Download className="h-4 w-4 mr-1" />
                  Export to CSV
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM Name</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Instance Type</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Storage</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Instance Cost</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Storage Cost</th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total VM Cost</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {sortedEstimates.slice(0, 5).map((estimate, index) => {
                      // Calculate storage cost (approximate $0.10 per GB per month)
                      const storageGB = estimate.current_storage_gb || 0;
                      const storageCost = storageGB * 0.10;
                      const instanceCost = estimate.projected_monthly_cost - storageCost;
                      
                      return (
                        <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{estimate.vm_name}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {estimate.recommended_instance_type} ({estimate.pricing_plan})
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {storageGB.toLocaleString()} GB
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            ${instanceCost.toLocaleString(undefined, {maximumFractionDigits: 2})}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            ${storageCost.toLocaleString(undefined, {maximumFractionDigits: 2})}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            ${estimate.projected_monthly_cost.toLocaleString(undefined, {maximumFractionDigits: 2})}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {sortedEstimates.length > 5 && (
                  <p className="text-sm text-gray-500 text-center mt-4">
                    Showing top 5 of {sortedEstimates.length} VMs by cost. Export to CSV for complete list.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
        {/* TCO Insight Section */}
        <div className="card mb-8">
          <div className="card-header bg-yellow-50">
            <h3 className="text-xl font-semibold text-gray-900">TCO Insights</h3>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Cost Optimization Opportunities</h4>
                <div className="space-y-4">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                      <span className="text-xs font-medium text-blue-600">1</span>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900">Right-sizing Instances</h5>
                      <p className="text-sm text-gray-600">
                        {Math.round(sortedEstimates.length * 0.3)} VMs could benefit from right-sizing based on utilization patterns
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                      <span className="text-xs font-medium text-blue-600">2</span>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900">Reserved Instances</h5>
                      <p className="text-sm text-gray-600">
                        Switching to 3-year Reserved Instances could save up to {Math.round(monthlyCost * 0.6).toLocaleString()} per month
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                      <span className="text-xs font-medium text-blue-600">3</span>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900">Modernization</h5>
                      <p className="text-sm text-gray-600">
                        Implementing modernization opportunities could reduce monthly costs by {formatCurrency(state.modernizationAnalysis?.summary?.total_monthly_savings || 0)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Key TCO Factors</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Infrastructure</span>
                    <span className="font-medium">{Math.round((state.costEstimatesAnalysis?.cost_summary?.infrastructure_monthly_cost || 0) / monthlyCost * 100)}% of total cost</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Top 5 VMs</span>
                    <span className="font-medium">
                      {formatCurrency(sortedEstimates.slice(0, 5).reduce((sum, vm) => sum + (vm.projected_monthly_cost || 0), 0))} per month
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Production vs Non-Production</span>
                    <span className="font-medium">
                      {Math.round(sortedEstimates.filter(vm => 
                        vm.vm_name && (vm.vm_name.toLowerCase().includes('prod') || vm.vm_name.toLowerCase().includes('prd'))
                      ).length / sortedEstimates.length * 100)}% / {Math.round(sortedEstimates.filter(vm => 
                        vm.vm_name && !vm.vm_name.toLowerCase().includes('prod') && !vm.vm_name.toLowerCase().includes('prd')
                      ).length / sortedEstimates.length * 100)}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">5-Year Growth Projection</span>
                    <span className="font-medium">10% annual increase</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modernization Opportunities */}
        <div className="card mb-8">
          <div className="card-header bg-purple-50">
            <h3 className="text-xl font-semibold text-gray-900">Modernization Opportunities</h3>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              {/* Modernization Summary */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Optimization Summary</h4>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Opportunities</span>
                    <span className="font-medium">{modernizationOpportunities}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Monthly Savings Potential</span>
                    <span className="font-medium text-green-600">{formatCurrency(state.modernizationAnalysis?.summary?.total_monthly_savings || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Average Cost Reduction</span>
                    <span className="font-medium">{state.modernizationAnalysis?.summary?.average_savings_percentage?.toFixed(1) || 0}%</span>
                  </div>
                </div>
              </div>

              {/* Modernization Categories */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Modernization Categories</h4>
                <div className="space-y-3">
                  {modernizationByCategory.map((category, index) => (
                    <div key={index} className="flex justify-between items-center">
                      <span className="text-gray-600 capitalize">{category.category}</span>
                      <div className="flex items-center space-x-4">
                        <span className="font-medium">{category.count} opportunities</span>
                        <span className="font-medium text-green-600">{formatCurrency(category.savings)}/month</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* What If Chart - TCO for 5 years with modernization after 2 years */}
            <div className="mt-8">
              <h4 className="text-lg font-medium text-gray-900 mb-4">What If: Modernization After 2 Years</h4>
              <p className="text-sm text-gray-600 mb-4">
                This chart shows the potential 5-year TCO if modernization opportunities are implemented after year 2.
              </p>
              <div className="h-80">
                {whatIfData.baseTCO.length > 0 && whatIfData.modernizedTCO.length > 0 ? (
                  <Line
                    data={{
                      labels: whatIfData.labels,
                      datasets: [
                        {
                          label: 'Without Modernization',
                          data: whatIfData.baseTCO,
                          borderColor: 'rgb(239, 68, 68)',
                          backgroundColor: 'rgba(239, 68, 68, 0.5)',
                          tension: 0.1,
                          pointRadius: 5,
                          pointHoverRadius: 7,
                        },
                        {
                          label: 'With Modernization (Year 3+)',
                          data: whatIfData.modernizedTCO,
                          borderColor: 'rgb(34, 197, 94)',
                          backgroundColor: 'rgba(34, 197, 94, 0.5)',
                          tension: 0.1,
                          pointRadius: 5,
                          pointHoverRadius: 7,
                        },
                      ],
                    }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: {
                        legend: {
                          position: 'top',
                        },
                        tooltip: {
                          callbacks: {
                            label: function(context) {
                              let label = context.dataset.label || '';
                              if (label) {
                                label += ': ';
                              }
                              if (context.parsed.y !== null) {
                                label += '$' + context.parsed.y.toLocaleString(undefined, {maximumFractionDigits: 2});
                              }
                              return label;
                            }
                          }
                        }
                      },
                      scales: {
                        y: {
                          beginAtZero: true,
                          ticks: {
                            callback: function(value) {
                              return '$' + value.toLocaleString();
                            }
                          }
                        }
                      }
                    }}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <p className="text-gray-500">No data available for What If analysis</p>
                  </div>
                )}
              </div>
              <div className="mt-4 p-4 bg-green-50 rounded-lg">
                <div className="flex items-start">
                  <div className="flex-shrink-0">
                    <TrendingDown className="h-5 w-5 text-green-600" />
                  </div>
                  <div className="ml-3">
                    <h5 className="text-sm font-medium text-green-800">Potential 5-Year Savings</h5>
                    <p className="text-sm text-green-700 mt-1">
                      Implementing modernization after year 2 could save approximately 
                      {formatCurrency((state.modernizationAnalysis?.summary?.total_monthly_savings || 0) * 12 * 3)} over years 3-5.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        {/* Recommendations */}
        <div className="card mb-8">
          <div className="card-header bg-yellow-50">
            <h3 className="text-xl font-semibold text-gray-900">Recommendations & Next Steps</h3>
          </div>
          <div className="card-content">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Migration Strategy */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Migration Strategy</h4>
                <div className="space-y-4">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                      <span className="text-xs font-medium text-blue-600">1</span>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900">Assessment & Planning</h5>
                      <p className="text-sm text-gray-600">Complete detailed application dependency mapping and create migration runbooks</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                      <span className="text-xs font-medium text-blue-600">2</span>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900">Pilot Migration</h5>
                      <p className="text-sm text-gray-600">Start with low-risk development and test environments</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                      <span className="text-xs font-medium text-blue-600">3</span>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900">Production Migration</h5>
                      <p className="text-sm text-gray-600">Execute phased migration of production workloads with minimal downtime</p>
                    </div>
                  </div>
                  <div className="flex items-start">
                    <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mr-3 mt-0.5">
                      <span className="text-xs font-medium text-blue-600">4</span>
                    </div>
                    <div>
                      <h5 className="font-medium text-gray-900">Optimization</h5>
                      <p className="text-sm text-gray-600">Implement modernization opportunities and cost optimization measures</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Key Benefits */}
              <div>
                <h4 className="text-lg font-medium text-gray-900 mb-4">Key Benefits</h4>
                <div className="space-y-3">
                  <div className="flex items-center">
                    <Shield className="h-5 w-5 text-green-600 mr-3" />
                    <span className="text-gray-700">Enhanced security and compliance</span>
                  </div>
                  <div className="flex items-center">
                    <TrendingUp className="h-5 w-5 text-green-600 mr-3" />
                    <span className="text-gray-700">Improved scalability and performance</span>
                  </div>
                  <div className="flex items-center">
                    <DollarSign className="h-5 w-5 text-green-600 mr-3" />
                    <span className="text-gray-700">Cost optimization through modernization</span>
                  </div>
                  <div className="flex items-center">
                    <Cloud className="h-5 w-5 text-green-600 mr-3" />
                    <span className="text-gray-700">Access to AWS managed services</span>
                  </div>
                  <div className="flex items-center">
                    <Zap className="h-5 w-5 text-green-600 mr-3" />
                    <span className="text-gray-700">Faster time-to-market for new features</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* AI-Powered Report Downloads */}
        <ReportDownloadSection sessionId={sessionId} />

        {/* Report Footer */}
        <div className="card">
          <div className="card-content">
            <div className="flex justify-between items-center text-sm text-gray-600">
              <div>
                <p>Report generated on {formatDate(new Date().toISOString())}</p>
                <p>Analysis based on {totalVMs} virtual machines from RVTools export</p>
              </div>
              <div className="text-right">
                <p>VMware to AWS Migration TCO Analysis</p>
                <p>Session ID: {sessionId}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportsPhase;
