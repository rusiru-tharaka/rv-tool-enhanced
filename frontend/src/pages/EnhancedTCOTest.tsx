import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Download, ArrowLeft, Calculator, Settings, Filter, Info, AlertTriangle, CheckCircle } from 'lucide-react';
import { apiService } from '../services/api';
import TCOParametersForm from '../components/TCOParametersForm';

interface VMCostData {
  vmName: string;
  cpuCores: number;
  memoryGB: number;
  storageGB: number;
  recommendedInstanceType: string;
  instanceCost: number;
  storageCost: number;
  totalMonthlyCost: number;
  pricingPlan: string;
  operatingSystem: string;
  environment: string;
}

interface ScopeInfo {
  total_vms: number;
  in_scope_vms: number;
  out_of_scope_vms: number;
  out_of_scope_details: Array<{
    vm_name: string;
    reason: string;
    category: string;
  }>;
  filtering_applied: boolean;
  fallback_reason?: string;
}

interface TCOParameters {
  target_region: string;
  production_ri_years: number;
  include_network: boolean;
  include_observability: boolean;
  pricing_model: string;
  instance_family: string;
  exclude_poweroff_vms: boolean;
  poweroff_exclusion_type: 'all' | 'older_than_two_years';
  
  // Enhanced parameters
  production_pricing_model: string;
  non_production_pricing_model: string;
  savings_plan_commitment: string;
  savings_plan_payment: string;
  production_utilization_percent: number;
  non_production_utilization_percent: number;
  default_os_type: string;
}

const EnhancedTCOTest: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  
  // State management
  const [vmCosts, setVmCosts] = useState<VMCostData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalMonthlyCost, setTotalMonthlyCost] = useState(0);
  const [totalAnnualCost, setTotalAnnualCost] = useState(0);
  const [scopeInfo, setScopeInfo] = useState<ScopeInfo | null>(null);
  const [showScopeDetails, setShowScopeDetails] = useState(false);
  const [showParametersForm, setShowParametersForm] = useState(true);
  const [currentParameters, setCurrentParameters] = useState<TCOParameters | null>(null);
  const [calculationTime, setCalculationTime] = useState<string>('');

  console.log('🏗️ [Enhanced TCO Test] Component initialized');
  console.log('📋 [Enhanced TCO Test] Session ID:', sessionId);
  console.log('📊 [Enhanced TCO Test] Initial state - showParametersForm:', showParametersForm);

  const calculateEnhancedTCO = async (parameters: TCOParameters) => {
    try {
      console.log('🚀 [Enhanced TCO Test] Starting calculation for session:', sessionId);
      console.log('📋 [Enhanced TCO Test] User Parameters:', parameters);
      
      setLoading(true);
      setError(null);
      setCurrentParameters(parameters);
      const startTime = Date.now();

      console.log('🔗 [Enhanced TCO Test] API Endpoint:', `/enhanced-tco-test/${sessionId}`);

      const response = await apiService.post(`/enhanced-tco-test/${sessionId}`, parameters);
      const data = response.data;
      
      const endTime = Date.now();
      const calculationDuration = ((endTime - startTime) / 1000).toFixed(2);
      setCalculationTime(calculationDuration);
      
      console.log('📥 [Enhanced TCO Test] Raw API Response:', data);
      console.log('📊 [Enhanced TCO Test] Response Keys:', Object.keys(data));
      console.log('⏱️ [Enhanced TCO Test] Calculation Time:', calculationDuration, 'seconds');
      
      // Check if response contains an error
      if (data.error) {
        console.error('❌ [Enhanced TCO Test] Backend Error:', data.error);
        console.error('❌ [Enhanced TCO Test] Error Message:', data.message);
        throw new Error(data.message || data.error || 'Backend returned an error');
      }
      
      // Set scope information
      if (data.scope_info) {
        console.log('🎯 [Enhanced TCO Test] Scope Info Received:', data.scope_info);
        console.log('📊 [Enhanced TCO Test] Total VMs:', data.scope_info.total_vms);
        console.log('✅ [Enhanced TCO Test] In-Scope VMs:', data.scope_info.in_scope_vms);
        console.log('❌ [Enhanced TCO Test] Out-of-Scope VMs:', data.scope_info.out_of_scope_vms);
        console.log('🔍 [Enhanced TCO Test] Filtering Applied:', data.scope_info.filtering_applied);
        
        setScopeInfo(data.scope_info);
        
        if (data.scope_info.out_of_scope_details && data.scope_info.out_of_scope_details.length > 0) {
          console.log('📋 [Enhanced TCO Test] Out-of-Scope Details:', data.scope_info.out_of_scope_details);
          data.scope_info.out_of_scope_details.forEach((item: any, index: number) => {
            console.log(`   ${index + 1}. ${item.vm_name} - ${item.reason} (${item.category})`);
          });
        }
        
        if (data.scope_info.fallback_reason) {
          console.warn('⚠️ [Enhanced TCO Test] Fallback Mode:', data.scope_info.fallback_reason);
        }
      }
      
      // Process VM cost data
      if (data.vm_costs && Array.isArray(data.vm_costs)) {
        console.log('💰 [Enhanced TCO Test] VM Costs Received:', data.vm_costs.length, 'VMs');
        
        const processedVMCosts: VMCostData[] = data.vm_costs.map((vm: any, index: number) => {
          console.log(`💰 [Enhanced TCO Test] Processing VM ${index + 1}:`, vm.vm_name);
          console.log(`   Instance: ${vm.recommended_instance_type}, Cost: $${vm.total_monthly_cost}`);
          
          return {
            vmName: vm.vm_name || `VM-${index + 1}`,
            cpuCores: vm.cpu_cores || 0,
            memoryGB: vm.memory_gb || 0,
            storageGB: vm.storage_gb || 0,
            recommendedInstanceType: vm.recommended_instance_type || 'Unknown',
            instanceCost: vm.instance_cost || 0,
            storageCost: vm.storage_cost || 0,
            totalMonthlyCost: vm.total_monthly_cost || 0,
            pricingPlan: vm.pricing_plan || 'On-Demand',
            operatingSystem: vm.operating_system || 'Linux',
            environment: vm.environment || 'Unknown'
          };
        });
        
        setVmCosts(processedVMCosts);
        
        // Calculate totals
        const monthlyTotal = processedVMCosts.reduce((sum, vm) => sum + vm.totalMonthlyCost, 0);
        const annualTotal = monthlyTotal * 12;
        
        console.log('📊 [Enhanced TCO Test] Cost Summary:');
        console.log(`   Monthly Total: $${monthlyTotal.toFixed(2)}`);
        console.log(`   Annual Total: $${annualTotal.toFixed(2)}`);
        
        setTotalMonthlyCost(monthlyTotal);
        setTotalAnnualCost(annualTotal);
        
        // Hide parameters form after successful calculation
        setShowParametersForm(false);
        
      } else {
        console.warn('⚠️ [Enhanced TCO Test] No VM costs data received');
        throw new Error('No VM cost data received from backend');
      }
      
    } catch (err: any) {
      console.error('❌ [Enhanced TCO Test] Calculation Error:', err);
      setError(err.message || 'Failed to calculate Enhanced TCO');
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = () => {
    if (vmCosts.length === 0) return;

    console.log('📤 [Enhanced TCO Test] Exporting CSV with', vmCosts.length, 'VMs');

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
      'Operating System',
      'Environment'
    ];

    const csvContent = [
      headers.join(','),
      ...vmCosts.map(vm => [
        vm.vmName,
        vm.cpuCores,
        vm.memoryGB,
        vm.storageGB,
        vm.recommendedInstanceType,
        vm.instanceCost.toFixed(2),
        vm.storageCost.toFixed(2),
        vm.totalMonthlyCost.toFixed(2),
        vm.pricingPlan,
        vm.operatingSystem,
        vm.environment
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `enhanced-tco-test-${sessionId}-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log('✅ [Enhanced TCO Test] CSV export completed');
  };

  const resetCalculation = () => {
    console.log('🔄 [Enhanced TCO Test] Resetting calculation');
    setShowParametersForm(true);
    setVmCosts([]);
    setTotalMonthlyCost(0);
    setTotalAnnualCost(0);
    setScopeInfo(null);
    setError(null);
    setCurrentParameters(null);
    setCalculationTime('');
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(-1)}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="h-5 w-5 mr-2" />
                Back
              </button>
              <div>
                <div className="flex items-center space-x-3">
                  <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                    <Calculator className="h-8 w-8 mr-3 text-blue-600" />
                    Enhanced TCO Test Calculator
                  </h1>
                  <span className="px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
                    Testing Mode
                  </span>
                </div>
                <p className="text-gray-600 mt-1">
                  Test Enhanced TCO calculations with user-defined parameters
                </p>
                <p className="text-sm text-blue-600 mt-1">
                  🆕 Opened in new tab for side-by-side comparison - configure parameters below
                </p>
              </div>
            </div>
            
            {!showParametersForm && (
              <div className="flex space-x-3">
                <button
                  onClick={resetCalculation}
                  className="btn-secondary"
                >
                  <Settings className="h-4 w-4 mr-2" />
                  New Calculation
                </button>
                <button
                  onClick={exportToCSV}
                  className="btn-primary"
                  disabled={vmCosts.length === 0}
                >
                  <Download className="h-4 w-4 mr-2" />
                  Export CSV
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Parameters Form */}
        {showParametersForm && (
          <div className="mb-8">
            <div className="card border-2 border-blue-200 bg-blue-50">
              <div className="card-header bg-blue-100">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-semibold text-blue-900 flex items-center">
                      <Settings className="h-5 w-5 mr-2" />
                      Enhanced TCO Parameters
                    </h2>
                    <p className="text-blue-700 mt-1">
                      Configure your TCO calculation parameters for testing
                    </p>
                  </div>
                  <div className="text-sm text-blue-600 bg-white px-3 py-1 rounded-full">
                    🧪 Test Mode Active
                  </div>
                </div>
              </div>
              <div className="card-content bg-white">
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center">
                    <Info className="h-5 w-5 text-blue-600 mr-2" />
                    <div className="text-sm text-blue-800">
                      <p className="font-medium">Enhanced TCO Test Mode - New Tab</p>
                      <p>This page opened in a new tab for easy comparison. Configure parameters below, then click "Calculate Enhanced TCO" to test with your settings.</p>
                    </div>
                  </div>
                </div>
                <TCOParametersForm
                  onCalculate={calculateEnhancedTCO}
                  isLoading={loading}
                />
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="card">
            <div className="card-content">
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-4"></div>
                <div>
                  <p className="text-lg font-medium text-gray-900">Calculating Enhanced TCO...</p>
                  <p className="text-gray-600">Processing VM data and calculating costs</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="card border-red-200 bg-red-50">
            <div className="card-content">
              <div className="flex items-center">
                <AlertTriangle className="h-6 w-6 text-red-600 mr-3" />
                <div>
                  <h3 className="text-lg font-medium text-red-900">Calculation Error</h3>
                  <p className="text-red-700 mt-1">{error}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {!loading && !error && vmCosts.length > 0 && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div className="card">
                <div className="card-content">
                  <div className="flex items-center">
                    <CheckCircle className="h-8 w-8 text-green-600" />
                    <div className="ml-4">
                      <p className="text-2xl font-semibold text-gray-900">
                        ${totalMonthlyCost.toLocaleString(undefined, {maximumFractionDigits: 0})}
                      </p>
                      <p className="text-sm text-gray-600">Monthly Cost</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-content">
                  <div className="flex items-center">
                    <Calculator className="h-8 w-8 text-blue-600" />
                    <div className="ml-4">
                      <p className="text-2xl font-semibold text-gray-900">
                        ${totalAnnualCost.toLocaleString(undefined, {maximumFractionDigits: 0})}
                      </p>
                      <p className="text-sm text-gray-600">Annual Cost</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="card">
                <div className="card-content">
                  <div className="flex items-center">
                    <Info className="h-8 w-8 text-purple-600" />
                    <div className="ml-4">
                      <p className="text-2xl font-semibold text-gray-900">
                        {vmCosts.length}
                      </p>
                      <p className="text-sm text-gray-600">VMs Processed</p>
                      {calculationTime && (
                        <p className="text-xs text-gray-500">in {calculationTime}s</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Scope Information */}
            {scopeInfo && (
              <div className="card mb-8">
                <div className="card-header">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-medium text-gray-900 flex items-center">
                      <Filter className="h-5 w-5 mr-2" />
                      Scope Information
                    </h3>
                    {scopeInfo.out_of_scope_vms > 0 && (
                      <button
                        onClick={() => setShowScopeDetails(!showScopeDetails)}
                        className="text-sm text-blue-600 hover:text-blue-800"
                      >
                        {showScopeDetails ? 'Hide' : 'Show'} Details
                      </button>
                    )}
                  </div>
                </div>
                <div className="card-content">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p className="text-2xl font-semibold text-gray-900">{scopeInfo.total_vms}</p>
                      <p className="text-sm text-gray-600">Total VMs</p>
                    </div>
                    <div>
                      <p className="text-2xl font-semibold text-green-600">{scopeInfo.in_scope_vms}</p>
                      <p className="text-sm text-gray-600">In-Scope VMs</p>
                    </div>
                    <div>
                      <p className="text-2xl font-semibold text-red-600">{scopeInfo.out_of_scope_vms}</p>
                      <p className="text-sm text-gray-600">Out-of-Scope VMs</p>
                    </div>
                  </div>

                  {showScopeDetails && scopeInfo.out_of_scope_details && scopeInfo.out_of_scope_details.length > 0 && (
                    <div className="mt-6 border-t pt-4">
                      <h4 className="font-medium text-gray-900 mb-3">Out-of-Scope VMs:</h4>
                      <div className="space-y-2">
                        {scopeInfo.out_of_scope_details.map((item, index) => (
                          <div key={index} className="flex items-center justify-between bg-red-50 p-3 rounded-lg">
                            <div>
                              <p className="font-medium text-red-900">{item.vm_name}</p>
                              <p className="text-sm text-red-700">{item.reason}</p>
                            </div>
                            <span className="px-2 py-1 bg-red-200 text-red-800 text-xs rounded-full">
                              {item.category}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {scopeInfo.fallback_reason && (
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <div className="flex items-center">
                        <AlertTriangle className="h-5 w-5 text-yellow-600 mr-2" />
                        <p className="text-sm text-yellow-800">
                          <strong>Fallback Mode:</strong> {scopeInfo.fallback_reason}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Current Parameters Display */}
            {currentParameters && (
              <div className="card mb-8">
                <div className="card-header">
                  <h3 className="text-lg font-medium text-gray-900">Current Parameters</h3>
                </div>
                <div className="card-content">
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="font-medium text-gray-700">Target Region</p>
                      <p className="text-gray-900">{currentParameters.target_region}</p>
                    </div>
                    <div>
                      <p className="font-medium text-gray-700">Production Pricing</p>
                      <p className="text-gray-900">{currentParameters.production_pricing_model}</p>
                    </div>
                    <div>
                      <p className="font-medium text-gray-700">Non-Production Pricing</p>
                      <p className="text-gray-900">{currentParameters.non_production_pricing_model}</p>
                    </div>
                    <div>
                      <p className="font-medium text-gray-700">Production Utilization</p>
                      <p className="text-gray-900">{currentParameters.production_utilization_percent}%</p>
                    </div>
                    <div>
                      <p className="font-medium text-gray-700">Non-Production Utilization</p>
                      <p className="text-gray-900">{currentParameters.non_production_utilization_percent}%</p>
                    </div>
                    <div>
                      <p className="font-medium text-gray-700">Default OS</p>
                      <p className="text-gray-900">{currentParameters.default_os_type}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* VM Cost Details Table */}
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-medium text-gray-900">VM Cost Details</h3>
              </div>
              <div className="card-content">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VM Name</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Instance Type</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Specs</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Instance Cost</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Storage Cost</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Total Cost</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Environment</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {vmCosts.map((vm, index) => (
                        <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            {vm.vmName}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <div>
                              <p className="font-medium">{vm.recommendedInstanceType}</p>
                              <p className="text-xs text-gray-400">{vm.pricingPlan}</p>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <div>
                              <p>{vm.cpuCores} vCPU, {vm.memoryGB} GB RAM</p>
                              <p className="text-xs text-gray-400">{vm.storageGB.toFixed(1)} GB storage</p>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            ${vm.instanceCost.toFixed(2)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            ${vm.storageCost.toFixed(2)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                            ${vm.totalMonthlyCost.toFixed(2)}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              vm.environment === 'Production' 
                                ? 'bg-blue-100 text-blue-800' 
                                : 'bg-green-100 text-green-800'
                            }`}>
                              {vm.environment}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default EnhancedTCOTest;
