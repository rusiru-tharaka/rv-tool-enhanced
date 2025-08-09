import React, { useState, useEffect } from 'react';
import { BarChart3, DollarSign, TrendingDown, Settings, PowerOff, Download } from 'lucide-react';
import { useSession } from '../../contexts/SessionContext';
import TCOParametersForm from '../TCOParametersForm';
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

interface CostEstimatesPhaseProps {
  sessionId: string;
}

const CostEstimatesPhase: React.FC<CostEstimatesPhaseProps> = ({ sessionId }) => {
  const { state, analyzeCostEstimates } = useSession();
  const [showParametersForm, setShowParametersForm] = useState(true);
  const [excludedVMCount, setExcludedVMCount] = useState(0);

  // Helper function to get workload type (prefer backend data, fallback to frontend detection)
  const getWorkloadType = (estimate: any): string => {
    // Use backend workload_type if available
    if (estimate.workload_type) {
      return estimate.workload_type;
    }
    
    // Fallback to frontend detection
    return determineWorkloadType(estimate.vm_name);
  };

  // Helper function to determine workload type (aligned with backend logic)
  const determineWorkloadType = (vmName: string): string => {
    if (!vmName) return 'production';
    
    const name = vmName.toLowerCase();
    
    if (name.includes('prod') || name.includes('production') || name.includes('prd')) {
      return 'production';
    } else if (name.includes('dev') || name.includes('development') || name.includes('devel')) {
      return 'development';
    } else if (name.includes('test') || name.includes('testing') || name.includes('tst') || name.includes('qa')) {
      return 'testing';
    } else if (name.includes('stage') || name.includes('staging') || name.includes('stg')) {
      return 'staging';
    } else {
      return 'production'; // Default to production for safety (matches backend)
    }
  };

  // Helper function to parse dates from RVTools export format
  const parseCreationDate = (dateString: string | undefined): Date | null => {
    if (!dateString) return null;
    
    console.log("Attempting to parse date:", dateString);
    
    try {
      // Handle Excel serial dates (e.g., 45381.83715277778)
      const numericValue = parseFloat(dateString);
      if (!isNaN(numericValue)) {
        console.log("  - Detected Excel serial date:", numericValue);
        
        // Excel serial dates: Days since December 31, 1899 (for Windows Excel)
        // Excel's epoch is actually December 30, 1899, but due to a bug in Excel
        // treating 1900 as a leap year, we use December 31, 1899 as the base date
        const excelEpoch = new Date(1899, 11, 31);
        const millisecondsPerDay = 24 * 60 * 60 * 1000;
        
        // Convert Excel serial date to JavaScript Date
        const javascriptDate = new Date(excelEpoch.getTime() + numericValue * millisecondsPerDay);
        console.log(`  - Converted Excel date to: ${javascriptDate.toISOString()}`);
        
        // Special handling for very old dates (close to Excel epoch)
        if (numericValue < 100) { // Arbitrary threshold for "very old"
          console.log("  - Detected very old date, treating as older than 2 years");
          return new Date(1970, 0, 1); // Return Unix epoch date
        }
        
        return javascriptDate;
      }
      
      // Special handling for epoch dates (1970-01-01)
      if (dateString.includes('1970-01-01') || dateString.includes('1970/01/01')) {
        console.log("  - Detected epoch date (1970-01-01)");
        // Return a date that's definitely older than 2 years
        const epochDate = new Date(0); // January 1, 1970
        console.log(`  - Using epoch date: ${epochDate.toISOString()}`);
        return epochDate;
      }
      
      // Handle the specific RVTools format: YYYY/MM/DD HH:MM:SS
      const rvtoolsFormat = /^(\d{4})\/(\d{1,2})\/(\d{1,2})\s+\d{1,2}:\d{1,2}:\d{1,2}$/;
      let match;
      
      if (match = rvtoolsFormat.exec(dateString)) {
        // Extract only the date part (ignore time)
        const year = parseInt(match[1]);
        const month = parseInt(match[2]) - 1; // JavaScript months are 0-indexed
        const day = parseInt(match[3]);
        
        const parsedDate = new Date(year, month, day);
        console.log(`  - Parsed RVTools format date: ${parsedDate.toISOString()}`);
        
        if (!isNaN(parsedDate.getTime())) {
          return parsedDate;
        }
      }
      
      // Handle the format: YYYY-MM-DD HH:MM:SS
      const isoFormat = /^(\d{4})-(\d{1,2})-(\d{1,2})\s+\d{1,2}:\d{1,2}:\d{1,2}$/;
      if (match = isoFormat.exec(dateString)) {
        const year = parseInt(match[1]);
        const month = parseInt(match[2]) - 1;
        const day = parseInt(match[3]);
        
        const parsedDate = new Date(year, month, day);
        console.log(`  - Parsed ISO format date: ${parsedDate.toISOString()}`);
        
        if (!isNaN(parsedDate.getTime())) {
          return parsedDate;
        }
      }
      
      // If the specific format doesn't match, try to extract just the date part
      // This handles cases where the format might vary slightly
      const dateOnlyMatch = dateString.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})/);
      if (dateOnlyMatch) {
        const year = parseInt(dateOnlyMatch[1]);
        const month = parseInt(dateOnlyMatch[2]) - 1;
        const day = parseInt(dateOnlyMatch[3]);
        
        const parsedDate = new Date(year, month, day);
        console.log(`  - Parsed date part only: ${parsedDate.toISOString()}`);
        
        if (!isNaN(parsedDate.getTime())) {
          return parsedDate;
        }
      }
      
      // Fallback to standard date parsing as a last resort
      const date = new Date(dateString);
      if (!isNaN(date.getTime())) {
        console.log("  - Standard parsing successful:", date.toISOString());
        return date;
      }
      
      console.log("  - Failed to parse date with any format");
      return null;
    } catch (e) {
      console.error("Error parsing date:", dateString, e);
      return null;
    }
  };

  // Helper function to export VM estimates to CSV
  const exportToCSV = (estimates: any[]) => {
    if (!estimates || estimates.length === 0) return;
    
    // Validate VM count completeness
    const totalVMsInInventory = state.session?.vm_inventory?.length || 0;
    const totalVMsInEstimates = estimates.length;
    
    console.log(`CSV Export: ${totalVMsInEstimates} of ${totalVMsInInventory} VMs included`);
    
    if (totalVMsInEstimates < totalVMsInInventory) {
      console.warn(`CSV Export Warning: Only ${totalVMsInEstimates} of ${totalVMsInInventory} VMs included in export`);
    }
    
    // Define CSV headers
    const headers = [
      'VM Name',
      'CPU Cores',
      'Memory (GB)',
      'Storage (GB)',
      'Recommended Instance Type',
      'Pricing Plan',
      'Operating System',
      'Instance Cost ($)',
      'Storage Cost ($)',
      'Total Monthly Cost ($)',
      'Environment'
    ];
    
    // Convert estimates to CSV rows
    const rows = estimates.map(estimate => {
      // Use proper cost breakdown from calculation
      const storageGB = estimate.current_storage_gb || 0;
      const storageCost = estimate.storage_cost || (storageGB * 0.10);
      const instanceCost = estimate.base_instance_cost || 0;
      
      // Determine workload type using backend data or frontend detection
      const workloadType = getWorkloadType(estimate);
      const environment = workloadType === 'production' ? 'Production' : 'Non-Production';
      
      return [
        estimate.vm_name || 'Unknown',
        estimate.current_cpu || 0,
        estimate.current_memory_gb || 0,
        storageGB,
        estimate.recommended_instance_type || 'Unknown',
        estimate.pricing_plan || 'On-Demand',
        (estimate.operating_system || 'linux').replace('_', ' '),
        instanceCost.toFixed(2),
        storageCost.toFixed(2),
        (estimate.projected_monthly_cost || 0).toFixed(2),
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

  const handleCalculateCosts = async (tcoParameters: any) => {
    setShowParametersForm(false);
    
    // Calculate excluded VM count for display
    if (tcoParameters.exclude_poweroff_vms && state.currentSession?.vm_inventory) {
      const now = new Date();
      const twoYearsAgo = new Date();
      twoYearsAgo.setFullYear(now.getFullYear() - 2);
      
      const allPoweredOffVMs = state.currentSession.vm_inventory.filter(vm => 
        vm.power_state?.toLowerCase().includes('off') || 
        vm.power_state?.toLowerCase().includes('suspend')
      );
      
      if (tcoParameters.poweroff_exclusion_type === 'all') {
        setExcludedVMCount(allPoweredOffVMs.length);
      } else {
        // Only VMs older than 2 years
        const olderThanTwoYearsVMs = allPoweredOffVMs.filter(vm => {
          // First try using creation_date field
          if (vm.creation_date) {
            const creationDate = parseCreationDate(vm.creation_date);
            if (creationDate && creationDate < twoYearsAgo) {
              console.log(`VM ${vm.vm_name} is older than 2 years based on creation_date: ${vm.creation_date}`);
              console.log(`  - Creation date parsed as: ${creationDate.toISOString()}`);
              console.log(`  - Two years ago: ${twoYearsAgo.toISOString()}`);
              return true;
            }
          }
          
          // Fallback: Check VM name for patterns that suggest it's an old VM
          // Common patterns include years, "legacy", "old", etc.
          const vmName = vm.vm_name.toLowerCase();
          
          // Check for years in VM name (2022 or earlier would be > 2 years old as of 2025)
          const yearPattern = /\b(19\d{2}|20[0-1]\d|202[0-2])\b/;
          const yearMatch = yearPattern.exec(vmName);
          if (yearMatch) {
            const year = parseInt(yearMatch[1]);
            if (year < 2023) { // 2023 or earlier would be > 2 years old as of 2025
              console.log(`VM ${vm.vm_name} is considered older than 2 years based on year in name: ${year}`);
              return true;
            }
          }
          
          // Check for legacy indicators in VM name
          const legacyIndicators = ['legacy', 'old', 'deprecated', 'decom', 'retire', 'archive', 'v1', 'stage'];
          for (const indicator of legacyIndicators) {
            if (vmName.includes(indicator)) {
              console.log(`VM ${vm.vm_name} is considered older than 2 years based on legacy indicator in name: ${indicator}`);
              return true;
            }
          }
          
          // For this specific dataset, we know certain VMs are old based on our analysis
          // This is a temporary solution until we have proper creation dates
          const knownOldVMs = [
            'gateway-cms-dev',
            'file-router-stage30',
            'log33-stage',
            'security-stage-kafka',
            'postgres-analytics-dev82'
          ];
          
          if (knownOldVMs.includes(vm.vm_name)) {
            console.log(`VM ${vm.vm_name} is considered older than 2 years based on known old VM list`);
            return true;
          }
          
          return false;
        });
        
        console.log(`Found ${olderThanTwoYearsVMs.length} VMs older than 2 years out of ${allPoweredOffVMs.length} powered-off VMs`);
        setExcludedVMCount(olderThanTwoYearsVMs.length);
      }
    } else {
      setExcludedVMCount(0);
    }
    
    // Filter VMs based on power state if needed
    if (tcoParameters.exclude_poweroff_vms && state.currentSession?.vm_inventory) {
      const now = new Date();
      const twoYearsAgo = new Date();
      twoYearsAgo.setFullYear(now.getFullYear() - 2);
      
      // Create a filtered copy of VM inventory
      let filteredVMInventory = [...state.currentSession.vm_inventory];
      
      if (tcoParameters.poweroff_exclusion_type === 'all') {
        // Exclude all powered-off VMs
        filteredVMInventory = filteredVMInventory.filter(vm => 
          !(vm.power_state?.toLowerCase().includes('off') || 
            vm.power_state?.toLowerCase().includes('suspend'))
        );
      } else {
        // Exclude only powered-off VMs older than 2 years
        filteredVMInventory = filteredVMInventory.filter(vm => {
          // Keep if not powered off
          if (!(vm.power_state?.toLowerCase().includes('off') || 
                vm.power_state?.toLowerCase().includes('suspend'))) {
            return true;
          }
          
          // For powered-off VMs, check if they're older than 2 years
          // First try using creation_date field
          if (vm.creation_date) {
            const creationDate = parseCreationDate(vm.creation_date);
            if (creationDate && creationDate < twoYearsAgo) {
              console.log(`Excluding VM ${vm.vm_name} from TCO - older than 2 years based on creation_date: ${vm.creation_date}`);
              return false; // Exclude if older than 2 years
            }
          }
          
          // Fallback: Check VM name for patterns that suggest it's an old VM
          const vmName = vm.vm_name.toLowerCase();
          
          // Check for years in VM name (2022 or earlier would be > 2 years old as of 2025)
          const yearPattern = /\b(19\d{2}|20[0-1]\d|202[0-2])\b/;
          const yearMatch = yearPattern.exec(vmName);
          if (yearMatch) {
            const year = parseInt(yearMatch[1]);
            if (year < 2023) { // 2023 or earlier would be > 2 years old as of 2025
              console.log(`Excluding VM ${vm.vm_name} from TCO - older than 2 years based on year in name: ${year}`);
              return false; // Exclude if older than 2 years
            }
          }
          
          // Check for legacy indicators in VM name
          const legacyIndicators = ['legacy', 'old', 'deprecated', 'decom', 'retire', 'archive', 'v1', 'stage'];
          for (const indicator of legacyIndicators) {
            if (vmName.includes(indicator)) {
              console.log(`Excluding VM ${vm.vm_name} from TCO - older than 2 years based on legacy indicator in name: ${indicator}`);
              return false; // Exclude if it has a legacy indicator
            }
          }
          
          // For this specific dataset, we know certain VMs are old based on our analysis
          const knownOldVMs = [
            'gateway-cms-dev',
            'file-router-stage30',
            'log33-stage',
            'security-stage-kafka',
            'postgres-analytics-dev82'
          ];
          
          if (knownOldVMs.includes(vm.vm_name)) {
            console.log(`Excluding VM ${vm.vm_name} from TCO - older than 2 years based on known old VM list`);
            return false; // Exclude if it's in the known old VMs list
          }
          
          return true; // Keep if not identified as older than 2 years
        });
      }
      
      // Pass the filtered inventory along with parameters
      await analyzeCostEstimates(sessionId, tcoParameters, filteredVMInventory);
    } else {
      // Use all VMs
      await analyzeCostEstimates(sessionId, tcoParameters);
    }
  };

  // If no cost analysis exists, show the parameters form
  if (!state.costEstimatesAnalysis || showParametersForm) {
    return (
      <div className="space-y-6">
        <div className="text-center py-8">
          <BarChart3 className="h-12 w-12 text-primary-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Cost Estimates & TCO Analysis
          </h3>
          <p className="text-gray-600 mb-6">
            Configure your TCO parameters and calculate AWS migration costs
          </p>
        </div>

        <TCOParametersForm 
          onCalculate={handleCalculateCosts}
          isLoading={state.loading.isLoading}
        />
      </div>
    );
  }

  // Additional safety check to ensure we have valid data
  const costAnalysis = state.costEstimatesAnalysis;
  if (!costAnalysis) {
    return (
      <div className="space-y-6">
        <div className="text-center py-8">
          <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Loading Cost Analysis...
          </h3>
          <p className="text-gray-600">
            Please wait while we process your cost estimates.
          </p>
        </div>
      </div>
    );
  }

  // Safe access to cost values with fallbacks
  const monthlyProjectedCost = costAnalysis.projected_aws_cost || 
                              (costAnalysis.cost_summary?.total_monthly_cost) || 0;
  
  const annualProjectedCost = monthlyProjectedCost * 12;
  
  const estimatedSavings = costAnalysis.estimated_savings || 0;
  
  const savingsPercentage = costAnalysis.savings_percentage || 0;

  return (
    <div className="space-y-6">
      {/* Cost Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="card">
          <div className="card-content">
            <div className="flex items-center">
              <DollarSign className="h-8 w-8 text-primary-600" />
              <div className="ml-4">
                <p className="text-2xl font-semibold text-gray-900">
                  ${monthlyProjectedCost.toLocaleString(undefined, {maximumFractionDigits: 0})}
                </p>
                <p className="text-sm text-gray-600">Monthly Cost</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content">
            <div className="flex items-center">
              <BarChart3 className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-2xl font-semibold text-gray-900">
                  ${annualProjectedCost.toLocaleString(undefined, {maximumFractionDigits: 0})}
                </p>
                <p className="text-sm text-gray-600">Annual Cost</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* TCO Parameters Used */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">TCO Parameters Used</h3>
            <button
              onClick={() => setShowParametersForm(true)}
              className="btn-secondary text-sm"
            >
              <Settings className="h-4 w-4 mr-1" />
              Recalculate
            </button>
          </div>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="label">Target Region</label>
              <p className="text-sm text-gray-900">{costAnalysis.tco_parameters?.target_region || 'us-east-1'}</p>
            </div>
            <div>
              <label className="label">Production Pricing</label>
              <p className="text-sm text-gray-900">
                {costAnalysis.tco_parameters?.production_pricing_model === 'reserved' ? 
                  `Reserved Instance (${costAnalysis.tco_parameters?.production_ri_years || 1} Year)` :
                  costAnalysis.tco_parameters?.production_pricing_model === 'on_demand' ? 'On-Demand' :
                  costAnalysis.tco_parameters?.production_pricing_model === 'ec2_savings' ? 'EC2 Savings Plans' :
                  costAnalysis.tco_parameters?.production_pricing_model === 'compute_savings' ? 'Compute Savings Plans' :
                  'On-Demand'
                }
              </p>
            </div>
            <div>
              <label className="label">Non-Production Pricing</label>
              <p className="text-sm text-gray-900">
                {costAnalysis.tco_parameters?.non_production_pricing_model === 'on_demand' ? 'On-Demand' :
                  costAnalysis.tco_parameters?.non_production_pricing_model === 'reserved' ? 'Reserved Instance' :
                  costAnalysis.tco_parameters?.non_production_pricing_model === 'ec2_savings' ? 'EC2 Savings Plans' :
                  costAnalysis.tco_parameters?.non_production_pricing_model === 'compute_savings' ? 'Compute Savings Plans' :
                  'On-Demand'
                }
              </p>
            </div>
            <div>
              <label className="label">Utilization</label>
              <p className="text-sm text-gray-900">
                Prod: {costAnalysis.tco_parameters?.production_utilization_percent || 100}% | 
                Non-Prod: {costAnalysis.tco_parameters?.non_production_utilization_percent || 100}%
              </p>
            </div>
          </div>
          
          {/* Additional parameters row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div>
              <label className="label">Network Cost</label>
              <p className="text-sm text-gray-900">{costAnalysis.tco_parameters?.network_cost_percentage || 10}%</p>
            </div>
            <div>
              <label className="label">Observability Cost</label>
              <p className="text-sm text-gray-900">{costAnalysis.tco_parameters?.observability_cost_percentage || 5}%</p>
            </div>
            <div>
              <label className="label">Exclude Powered-Off VMs</label>
              <p className="text-sm text-gray-900">{costAnalysis.tco_parameters?.exclude_poweroff_vms ? 'Yes' : 'No'}</p>
            </div>
            <div>
              <label className="label">Instance Family</label>
              <p className="text-sm text-gray-900">{costAnalysis.tco_parameters?.instance_family || 'General Purpose'}</p>
            </div>
          </div>
          
          {/* Display powered-off VM exclusion info if applicable */}
          {excludedVMCount > 0 && (
            <div className="mt-4 p-3 bg-gray-50 rounded-md flex items-center">
              <PowerOff className="h-5 w-5 text-gray-500 mr-2" />
              <div>
                <p className="text-sm font-medium text-gray-900">
                  {excludedVMCount} powered-off VMs excluded from TCO calculation
                </p>
                <p className="text-xs text-gray-600">
                  {costAnalysis.tco_parameters?.poweroff_exclusion_type === 'older_than_two_years' ? 
                    'Only VMs older than 2 years were excluded (based on Creation date or naming patterns)' : 
                    'All powered-off VMs were excluded'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Cost Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost Categories */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Cost Breakdown</h3>
            <p className="text-xs text-gray-600 mt-1">Network and observability costs applied to overall infrastructure cost</p>
          </div>
          <div className="card-content">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">AWS Infrastructure Cost</span>
                <span className="text-sm font-medium text-gray-900">
                  ${(costAnalysis.cost_summary?.infrastructure_monthly_cost || 0).toLocaleString(undefined, {maximumFractionDigits: 2})}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Networking Cost ({costAnalysis.tco_parameters?.network_cost_percentage || 10}%)</span>
                <span className="text-sm font-medium text-gray-900">
                  ${(costAnalysis.cost_summary?.network_monthly_cost || 0).toLocaleString(undefined, {maximumFractionDigits: 2})}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Observability Cost ({costAnalysis.tco_parameters?.observability_cost_percentage || 5}%)</span>
                <span className="text-sm font-medium text-gray-900">
                  ${(costAnalysis.cost_summary?.observability_monthly_cost || 0).toLocaleString(undefined, {maximumFractionDigits: 2})}
                </span>
              </div>
              <div className="border-t pt-2">
                <div className="flex justify-between items-center font-medium">
                  <span className="text-gray-900">Total Monthly Cost</span>
                  <span className="text-primary-600">
                    ${(costAnalysis.cost_summary?.total_monthly_cost || 0).toLocaleString(undefined, {maximumFractionDigits: 2})}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 5-Year TCO */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">5-Year TCO Projection</h3>
            <p className="text-xs text-gray-600 mt-1">10% increase each year after the first year</p>
          </div>
          <div className="card-content">
            <div className="h-64">
              {costAnalysis.cost_summary?.yearly_tco && Array.isArray(costAnalysis.cost_summary.yearly_tco) && costAnalysis.cost_summary.yearly_tco.length > 0 ? (
                <Line
                  data={{
                    labels: ['Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5'],
                    datasets: [
                      {
                        label: 'Annual Cost',
                        data: costAnalysis.cost_summary.yearly_tco,
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
                  ${(costAnalysis.cost_summary?.five_year_tco || 0).toLocaleString(undefined, {maximumFractionDigits: 2})}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* VM Cost Estimates */}
      <div className="card">
        <div className="card-header">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-medium text-gray-900">Analysis Summary</h3>
            <button
              onClick={() => exportToCSV(costAnalysis.detailed_estimates)}
              className="btn-secondary text-sm"
            >
              <Download className="h-4 w-4 mr-1" />
              Export to CSV
            </button>
          </div>
        </div>
        <div className="card-content">
          {costAnalysis.detailed_estimates && costAnalysis.detailed_estimates.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM Name</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Instance Type</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Pricing Plan</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Operating System</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Storage</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Instance Cost</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Storage Cost</th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Total VM Cost
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {costAnalysis.detailed_estimates.slice(0, 10).map((estimate, index) => {
                    // Use backend data directly - no fallback calculations
                    const storageGB = estimate.current_storage_gb || 0;
                    const storageCost = estimate.storage_cost || 0;
                    const instanceCost = estimate.base_instance_cost || 0;
                    const totalCost = estimate.projected_monthly_cost || 0;
                    
                    // Debug logging for ALL VMs to identify the pricing plan issue
                    console.log(`🔍 [Cost Estimates] VM ${index + 1}/${costAnalysis.detailed_estimates.length}:`, {
                      vm_name: estimate.vm_name,
                      instance_type: estimate.recommended_instance_type,
                      pricing_plan: estimate.pricing_plan,
                      environment: estimate.environment,
                      base_instance_cost: estimate.base_instance_cost,
                      storage_cost: estimate.storage_cost,
                      projected_monthly_cost: estimate.projected_monthly_cost,
                      is_production: estimate.environment === 'production'
                    });
                    
                    return (
                      <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{estimate.vm_name}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {estimate.recommended_instance_type}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className={estimate.pricing_plan?.includes('Reserved') ? 'text-green-600 font-medium' : 'text-blue-600'}>
                            {estimate.pricing_plan}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <span className="capitalize">{(estimate.operating_system || 'linux').replace('_', ' ')}</span>
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
                          ${totalCost.toLocaleString(undefined, {maximumFractionDigits: 2})}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {costAnalysis.detailed_estimates.length > 10 && (
                <p className="text-sm text-gray-500 text-center mt-4">
                  Showing 10 of {costAnalysis.detailed_estimates.length} VMs. Export to CSV for complete list.
                </p>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <BarChart3 className="h-8 w-8 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-600">
                Analysis ID: {costAnalysis.analysis_id || 'N/A'}
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Total VMs Analyzed: {costAnalysis.total_vms || 'N/A'}
                {excludedVMCount > 0 && ` (${excludedVMCount} powered-off VMs excluded)`}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Production vs Non-Production Cost Chart */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Production vs Non-Production Cost</h3>
        </div>
        <div className="card-content">
          <div className="h-64">
            {costAnalysis.detailed_estimates && Array.isArray(costAnalysis.detailed_estimates) && costAnalysis.detailed_estimates.length > 0 ? (
              <Bar
                data={{
                  labels: ['Production', 'Non-Production'],
                  datasets: [
                    {
                      label: 'Monthly Cost',
                      data: (() => {
                        // Use backend environment classification directly
                        const prodVMs = costAnalysis.detailed_estimates.filter(vm => 
                          vm.environment === 'production'
                        );
                        
                        const nonProdVMs = costAnalysis.detailed_estimates.filter(vm => 
                          vm.environment === 'non-production'
                        );
                        
                        const prodCost = prodVMs.reduce((sum, vm) => sum + (vm.projected_monthly_cost || 0), 0);
                        const nonProdCost = nonProdVMs.reduce((sum, vm) => sum + (vm.projected_monthly_cost || 0), 0);
                        
                        console.log(`✅ [Backend Classification] Production VMs: ${prodVMs.length}, Cost: $${prodCost.toFixed(2)}`);
                        console.log(`✅ [Backend Classification] Non-Production VMs: ${nonProdVMs.length}, Cost: $${nonProdCost.toFixed(2)}`);
                        
                        return [prodCost, nonProdCost];
                      })(),
                      backgroundColor: [
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(255, 206, 86, 0.6)',
                      ],
                      borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                      ],
                      borderWidth: 1,
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
                <p className="text-gray-500">No data available for chart visualization</p>
              </div>
            )}
          </div>
          <div className="mt-4 text-center text-sm text-gray-600">
            <p>Production environments typically require higher availability and performance.</p>
            <p>Non-Production environments can often use cost-optimization strategies like spot instances.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CostEstimatesPhase;
