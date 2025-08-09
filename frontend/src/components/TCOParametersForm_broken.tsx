import React, { useState, useEffect } from 'react';
import { Settings, Calculator, PowerOff, Globe, Zap, Server, Clock } from 'lucide-react';
import { useSession } from '../contexts/SessionContext';

interface TCOParameters {
  target_region: string;
  production_ri_years: number;
  include_network: boolean;
  include_observability: boolean;
  pricing_model: string;
  instance_family: string;
  exclude_poweroff_vms: boolean;
  poweroff_exclusion_type: 'all' | 'older_than_two_years';
  
  // New enhanced parameters
  production_pricing_model: string;
  non_production_pricing_model: string;
  savings_plan_commitment: string;
  savings_plan_payment: string;
  production_utilization_percent: number;
  non_production_utilization_percent: number;
  default_os_type: string;
}

interface TCOParametersFormProps {
  onCalculate: (parameters: TCOParameters) => void;
  isLoading?: boolean;
}

interface AWSRegion {
  code: string;
  name: string;
  location: string;
  pricing_tier: string;
  supports_savings_plans: boolean;
}

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

    // Try parsing as ISO date string
    if (dateString.includes('T') || dateString.includes('-')) {
      const isoDate = new Date(dateString);
      if (!isNaN(isoDate.getTime())) {
        console.log("  - ISO parsing successful:", isoDate.toISOString());
        return isoDate;
      }
    }

    // Try parsing date-only format (YYYY-MM-DD or MM/DD/YYYY)
    const dateOnlyMatch = dateString.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/) || 
                          dateString.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    
    if (dateOnlyMatch) {
      let year, month, day;
      if (dateString.includes('-')) {
        // YYYY-MM-DD format
        year = parseInt(dateOnlyMatch[1]);
        month = parseInt(dateOnlyMatch[2]) - 1; // JavaScript months are 0-indexed
        day = parseInt(dateOnlyMatch[3]);
      } else {
        // MM/DD/YYYY format
        month = parseInt(dateOnlyMatch[1]) - 1; // JavaScript months are 0-indexed
        day = parseInt(dateOnlyMatch[2]);
        year = parseInt(dateOnlyMatch[3]);
      }
      
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

// Helper function to detect OS from VM data
const detectOperatingSystem = (vm: any): string => {
  const osField = vm.guest_os || vm.os || vm.operating_system || vm.guest_full_name || '';
  const osLower = osField.toLowerCase();
  
  if (osLower.includes('windows')) return 'windows';
  if (osLower.includes('rhel') || osLower.includes('red hat')) return 'rhel';
  if (osLower.includes('suse')) return 'suse';
  if (osLower.includes('ubuntu')) return 'ubuntu_pro';
  if (osLower.includes('linux') || osLower.includes('centos') || osLower.includes('debian')) return 'linux';
  
  // Default to linux if unknown
  return 'linux';
};

const TCOParametersFormEnhanced: React.FC<TCOParametersFormProps> = ({ onCalculate, isLoading = false }) => {
  const { state } = useSession();
  const [parameters, setParameters] = useState<TCOParameters>({
    target_region: 'us-east-1',
    production_ri_years: 1,
    include_network: true,
    include_observability: true,
    pricing_model: 'on_demand',
    instance_family: 'general_purpose',
    exclude_poweroff_vms: false,
    poweroff_exclusion_type: 'all',
    
    // New enhanced parameters
    production_pricing_model: 'reserved',
    non_production_pricing_model: 'on_demand',
    savings_plan_commitment: '1_year',
    savings_plan_payment: 'no_upfront',
    production_utilization_percent: 100,
    non_production_utilization_percent: 50,
    default_os_type: 'linux'
  });

  const [availableRegions, setAvailableRegions] = useState<AWSRegion[]>([]);
  const [osDistribution, setOsDistribution] = useState<{[key: string]: number}>({});
  
  // Count of powered-off VMs
  const [powerOffCounts, setPowerOffCounts] = useState({
    all: 0,
    olderThanTwoYears: 0
  });

  // Load available regions on component mount
  useEffect(() => {
    const loadRegions = async () => {
      try {
        const response = await fetch('/api/cost-estimates/regions');
        const data = await response.json();
        setAvailableRegions(data.regions || []);
      } catch (error) {
        console.error('Failed to load regions:', error);
        // Fallback to basic regions if API fails
        setAvailableRegions([
          { code: 'us-east-1', name: 'US East (N. Virginia)', location: 'US East (N. Virginia)', pricing_tier: 'standard', supports_savings_plans: true },
          { code: 'us-west-2', name: 'US West (Oregon)', location: 'US West (Oregon)', pricing_tier: 'standard', supports_savings_plans: true },
          { code: 'eu-west-1', name: 'Europe (Ireland)', location: 'Europe (Ireland)', pricing_tier: 'standard', supports_savings_plans: true },
          { code: 'ap-southeast-1', name: 'Asia Pacific (Singapore)', location: 'Asia Pacific (Singapore)', pricing_tier: 'standard', supports_savings_plans: true },
          { code: 'ap-northeast-1', name: 'Asia Pacific (Tokyo)', location: 'Asia Pacific (Tokyo)', pricing_tier: 'standard', supports_savings_plans: true }
        ]);
      }
    };
    
    loadRegions();
  }, []);

  // Analyze VM inventory for OS distribution and power state
  useEffect(() => {
    if (state.currentSession?.vm_inventory) {
      const now = new Date();
      const twoYearsAgo = new Date();
      twoYearsAgo.setFullYear(now.getFullYear() - 2);

      console.log("Analyzing VM inventory for enhanced parameters");
      console.log("Total VMs in inventory:", state.currentSession.vm_inventory.length);
      
      // Analyze OS distribution
      const osCount: {[key: string]: number} = {};
      let detectedDefaultOs = 'linux';
      let maxOsCount = 0;
      
      state.currentSession.vm_inventory.forEach(vm => {
        const os = detectOperatingSystem(vm);
        osCount[os] = (osCount[os] || 0) + 1;
        
        if (osCount[os] > maxOsCount) {
          maxOsCount = osCount[os];
          detectedDefaultOs = os;
        }
      });
      
      setOsDistribution(osCount);
      
      // Update default OS type based on most common OS
      setParameters(prev => ({
        ...prev,
        default_os_type: detectedDefaultOs
      }));

      // Calculate powered-off VM counts
      const allPoweredOffVMs = state.currentSession.vm_inventory.filter(vm => {
        const isPoweredOff = vm.power_state?.toLowerCase().includes('off') || 
                            vm.power_state?.toLowerCase().includes('suspend');
        return isPoweredOff;
      });

      const olderThanTwoYearsVMs = allPoweredOffVMs.filter(vm => {
        const creationDate = parseCreationDate(vm.creation_date);
        return creationDate && creationDate < twoYearsAgo;
      });

      setPowerOffCounts({
        all: allPoweredOffVMs.length,
        olderThanTwoYears: olderThanTwoYearsVMs.length
      });
      
      console.log("OS Distribution:", osCount);
      console.log("Detected default OS:", detectedDefaultOs);
      console.log("Powered-off VMs:", allPoweredOffVMs.length);
    }
  }, [state.currentSession?.vm_inventory]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCalculate(parameters);
  };

  const handleInputChange = (field: keyof TCOParameters, value: any) => {
    setParameters(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Get the count of VMs that will be excluded based on current selection
  const getExcludedVMCount = () => {
    if (!parameters.exclude_poweroff_vms) return 0;
    return parameters.poweroff_exclusion_type === 'all' ? 
      powerOffCounts.all : 
      powerOffCounts.olderThanTwoYears;
  };

  // Check if current region supports Savings Plans
  const currentRegionSupportsSavingsPlans = () => {
    const region = availableRegions.find(r => r.code === parameters.target_region);
    return region?.supports_savings_plans || false;
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center">
          <Settings className="h-5 w-5 text-primary-600 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">Enhanced TCO Parameters</h3>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          Configure comprehensive Total Cost of Ownership parameters with advanced pricing models
        </p>
      </div>
      
      <form onSubmit={handleSubmit} className="card-content space-y-8">
        
        {/* Regional Configuration Section */}
        <div className="space-y-4">
          <div className="flex items-center">
            <Globe className="h-4 w-4 text-primary-600 mr-2" />
            <h4 className="text-md font-medium text-gray-800">Regional Configuration</h4>
          </div>
          
          <div>
            <label className="label">Target AWS Region</label>
            <select
              value={parameters.target_region}
              onChange={(e) => handleInputChange('target_region', e.target.value)}
              className="input"
            >
              {availableRegions.map(region => (
                <option key={region.code} value={region.code}>
                  {region.name} ({region.code})
                  {region.pricing_tier === 'premium' && ' - Premium Pricing'}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              {availableRegions.length} regions available. 
              {currentRegionSupportsSavingsPlans() ? ' Savings Plans supported.' : ' Savings Plans not available in this region.'}
            </p>
          </div>
        </div>

        {/* Operating System Configuration */}
        <div className="space-y-4">
          <div className="flex items-center">
            <Server className="h-4 w-4 text-primary-600 mr-2" />
            <h4 className="text-md font-medium text-gray-800">Operating System Configuration</h4>
          </div>
          
          <div>
            <label className="label">Default Operating System Type</label>
            <select
              value={parameters.default_os_type}
              onChange={(e) => handleInputChange('default_os_type', e.target.value)}
              className="input"
            >
              <option value="linux">Linux</option>
              <option value="windows">Windows</option>
              <option value="rhel">Red Hat Enterprise Linux (RHEL)</option>
              <option value="suse">SUSE Linux</option>
              <option value="ubuntu_pro">Ubuntu Pro</option>
            </select>
            
            {Object.keys(osDistribution).length > 0 && (
              <div className="mt-2 p-3 bg-gray-50 rounded-md">
                <p className="text-xs font-medium text-gray-700 mb-2">Detected OS Distribution:</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(osDistribution).map(([os, count]) => (
                    <div key={os} className="flex justify-between">
                      <span className="capitalize">{os.replace('_', ' ')}:</span>
                      <span className="font-medium">{count} VMs</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Production Workload Pricing */}
        <div className="space-y-4">
          <div className="flex items-center">
            <Zap className="h-4 w-4 text-primary-600 mr-2" />
            <h4 className="text-md font-medium text-gray-800">Production Workload Pricing</h4>
          </div>
          
          <div>
            <label className="label">Production Pricing Model</label>
            <select
              value={parameters.production_pricing_model}
              onChange={(e) => handleInputChange('production_pricing_model', e.target.value)}
              className="input"
            >
              <option value="on_demand">On-Demand</option>
              <option value="reserved">Reserved Instances</option>
              {currentRegionSupportsSavingsPlans() && (
                <>
                  <option value="compute_savings">Compute Savings Plans</option>
                  <option value="ec2_savings">EC2 Instance Savings Plans</option>
                </>
              )}
            </select>
          </div>

          {/* Reserved Instance Configuration for Production */}
          {parameters.production_pricing_model === 'reserved' && (
            <div>
              <label className="label">Production Reserved Instance Term</label>
              <select
                value={parameters.production_ri_years}
                onChange={(e) => handleInputChange('production_ri_years', parseInt(e.target.value))}
                className="input"
              >
                <option value={1}>1 Year</option>
                <option value={3}>3 Years</option>
              </select>
            </div>
          )}

          {/* Savings Plans Configuration for Production */}
          {(parameters.production_pricing_model === 'compute_savings' || parameters.production_pricing_model === 'ec2_savings') && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Commitment Term</label>
                <select
                  value={parameters.savings_plan_commitment}
                  onChange={(e) => handleInputChange('savings_plan_commitment', e.target.value)}
                  className="input"
                >
                  <option value="1_year">1 Year</option>
                  <option value="3_year">3 Years</option>
                </select>
              </div>
              <div>
                <label className="label">Payment Option</label>
                <select
                  value={parameters.savings_plan_payment}
                  onChange={(e) => handleInputChange('savings_plan_payment', e.target.value)}
                  className="input"
                >
                  <option value="no_upfront">No Upfront</option>
                  <option value="partial_upfront">Partial Upfront</option>
                  <option value="all_upfront">All Upfront</option>
                </select>
              </div>
            </div>
          )}

          {/* Production Utilization */}
          {parameters.production_pricing_model === 'on_demand' && (
            <div>
              <label className="label">Production Utilization Percentage</label>
              <select
                value={parameters.production_utilization_percent}
                onChange={(e) => handleInputChange('production_utilization_percent', parseInt(e.target.value))}
                className="input"
              >
                <option value={25}>25% - Light Usage</option>
                <option value={50}>50% - Moderate Usage</option>
                <option value={75}>75% - Heavy Usage</option>
                <option value={100}>100% - Continuous Usage</option>
              </select>
            </div>
          )}
        </div>

        {/* Non-Production Workload Pricing */}
        <div className="space-y-4">
          <div className="flex items-center">
            <Clock className="h-4 w-4 text-primary-600 mr-2" />
            <h4 className="text-md font-medium text-gray-800">Non-Production Workload Pricing</h4>
          </div>
          
          <div>
            <label className="label">Non-Production Pricing Model</label>
            <select
              value={parameters.non_production_pricing_model}
              onChange={(e) => handleInputChange('non_production_pricing_model', e.target.value)}
              className="input"
            >
              <option value="on_demand">On-Demand</option>
              <option value="reserved">Reserved Instances</option>
              {currentRegionSupportsSavingsPlans() && (
                <>
                  <option value="compute_savings">Compute Savings Plans</option>
                  <option value="ec2_savings">EC2 Instance Savings Plans</option>
                </>
              )}
            </select>
          </div>

          {/* Non-Production Utilization */}
          {parameters.non_production_pricing_model === 'on_demand' && (
            <div>
              <label className="label">Non-Production Utilization Percentage</label>
              <select
                value={parameters.non_production_utilization_percent}
                onChange={(e) => handleInputChange('non_production_utilization_percent', parseInt(e.target.value))}
                className="input"
              >
                <option value={25}>25% - Development/Testing</option>
                <option value={50}>50% - Staging Environment</option>
                <option value={75}>75% - Pre-Production</option>
                <option value={100}>100% - Continuous Non-Prod</option>
              </select>
            </div>
          )}
        </div>

        {/* Instance Family Selection */}
        <div>
          <label className="label">Instance Family Preference</label>
          <select
            value={parameters.instance_family}
            onChange={(e) => handleInputChange('instance_family', e.target.value)}
            className="input"
          >
            <option value="general_purpose">General Purpose (M5, M6i)</option>
            <option value="compute_optimized">Compute Optimized (C5, C6i)</option>
            <option value="memory_optimized">Memory Optimized (R5, R6i)</option>
            <option value="storage_optimized">Storage Optimized (I3, I4i)</option>
            <option value="accelerated_computing">Accelerated Computing (P3, P4)</option>
          </select>
        </div>

        {/* Additional Cost Components */}
        <div className="space-y-4">
          <h4 className="text-md font-medium text-gray-800">Additional Cost Components</h4>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center">
              <input
                type="checkbox"
                id="include_network"
                checked={parameters.include_network}
                onChange={(e) => handleInputChange('include_network', e.target.checked)}
                className="mr-2"
              />
              <label htmlFor="include_network" className="text-sm text-gray-700">
                Include Network Costs (10%)
              </label>
            </div>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                id="include_observability"
                checked={parameters.include_observability}
                onChange={(e) => handleInputChange('include_observability', e.target.checked)}
                className="mr-2"
              />
              <label htmlFor="include_observability" className="text-sm text-gray-700">
                Include Observability Costs (5%)
              </label>
            </div>
          </div>
        </div>

        {/* VM Exclusion Options */}
        <div className="space-y-4">
          <div className="flex items-center">
            <PowerOff className="h-4 w-4 text-primary-600 mr-2" />
            <h4 className="text-md font-medium text-gray-800">VM Exclusion Options</h4>
          </div>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="exclude_poweroff_vms"
              checked={parameters.exclude_poweroff_vms}
              onChange={(e) => handleInputChange('exclude_poweroff_vms', e.target.checked)}
              className="mr-2"
            />
            <label htmlFor="exclude_poweroff_vms" className="text-sm text-gray-700">
              Exclude powered-off VMs from cost calculation
            </label>
          </div>

          {parameters.exclude_poweroff_vms && (
            <div className="ml-6 space-y-2">
              <div className="flex items-center">
                <input
                  type="radio"
                  id="exclude_all"
                  name="poweroff_exclusion_type"
                  value="all"
                  checked={parameters.poweroff_exclusion_type === 'all'}
                  onChange={(e) => handleInputChange('poweroff_exclusion_type', e.target.value)}
                  className="mr-2"
                />
                <label htmlFor="exclude_all" className="text-sm text-gray-600">
                  Exclude all powered-off VMs ({powerOffCounts.all} VMs)
                </label>
              </div>
              
              <div className="flex items-center">
                <input
                  type="radio"
                  id="exclude_old"
                  name="poweroff_exclusion_type"
                  value="older_than_two_years"
                  checked={parameters.poweroff_exclusion_type === 'older_than_two_years'}
                  onChange={(e) => handleInputChange('poweroff_exclusion_type', e.target.value)}
                  className="mr-2"
                />
                <label htmlFor="exclude_old" className="text-sm text-gray-600">
                  Exclude only VMs powered-off for 2+ years ({powerOffCounts.olderThanTwoYears} VMs)
                </label>
              </div>
            </div>
          )}
          
          {getExcludedVMCount() > 0 && (
            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-sm text-yellow-800">
                <strong>{getExcludedVMCount()}</strong> VMs will be excluded from cost calculation
              </p>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div className="pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary w-full flex items-center justify-center"
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Calculating Costs...
              </>
            ) : (
              <>
                <Calculator className="h-4 w-4 mr-2" />
                Calculate Enhanced TCO
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default TCOParametersFormEnhanced;
