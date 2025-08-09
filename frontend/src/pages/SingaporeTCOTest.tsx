import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Download, ArrowLeft, Calculator, MapPin } from 'lucide-react';
import { apiService } from '../services/api';

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

const SingaporeTCOTest: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [vmCosts, setVmCosts] = useState<VMCostData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalMonthlyCost, setTotalMonthlyCost] = useState(0);
  const [totalAnnualCost, setTotalAnnualCost] = useState(0);

  useEffect(() => {
    if (sessionId) {
      calculateSingaporeTCO();
    }
  }, [sessionId]);

  const calculateSingaporeTCO = async () => {
    try {
      setLoading(true);
      setError(null);

      // Hardcoded TCO parameters for Singapore test
      const tcoParameters = {
        target_region: 'ap-southeast-1',
        production_model: 'reserved_instance',
        reserved_instance_term: '3_year',
        reserved_instance_payment: 'no_upfront',
        non_production_model: 'on_demand',
        non_production_utilization: 0.5
      };

      const response = await apiService.post(`/singapore-tco-test/${sessionId}`, tcoParameters);
      const data = response.data;
      
      // Check if response contains an error
      if (data.error) {
        throw new Error(data.message || data.error || 'Backend returned an error');
      }
      
      // Check if response has the expected format
      if (data.vm_costs && Array.isArray(data.vm_costs)) {
        setVmCosts(data.vm_costs);
        
        // Calculate totals
        const monthlyTotal = data.vm_costs.reduce((sum: number, vm: VMCostData) => sum + vm.totalMonthlyCost, 0);
        setTotalMonthlyCost(monthlyTotal);
        setTotalAnnualCost(monthlyTotal * 12);
      } else if (data.vm_costs && data.vm_costs.length === 0) {
        // Handle empty results
        setVmCosts([]);
        setTotalMonthlyCost(0);
        setTotalAnnualCost(0);
        setError('No VM data found. Please make sure you have uploaded RVTools data and have a valid session.');
      } else {
        throw new Error('Invalid response format - missing vm_costs array');
      }
    } catch (err) {
      console.error('Error calculating Singapore TCO:', err);
      
      // Provide more helpful error messages
      let errorMessage = 'Failed to calculate Singapore TCO';
      
      if (err instanceof Error) {
        if (err.message.includes('Not Found') || err.message.includes('Session not found')) {
          errorMessage = 'Session not found. Please go back to the dashboard, upload your RVTools file, and try again.';
        } else if (err.message.includes('No VM data')) {
          errorMessage = 'No VM data found in this session. Please make sure you have uploaded RVTools data first.';
        } else if (err.message.includes('Network Error') || err.message.includes('Connection refused')) {
          errorMessage = 'Cannot connect to the backend server. Please make sure the backend is running.';
        } else {
          errorMessage = err.message;
        }
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = () => {
    if (vmCosts.length === 0) return;

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
        `"${vm.pricingPlan}"`,
        vm.operatingSystem,
        vm.environment
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `singapore-tco-test-${sessionId}-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Calculating Singapore TCO...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
            <h3 className="text-lg font-semibold text-red-800 mb-2">Error</h3>
            <p className="text-red-600 mb-4">{error}</p>
            <button
              onClick={() => navigate(-1)}
              className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
            >
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate(-1)}
                className="flex items-center text-gray-600 hover:text-gray-900"
              >
                <ArrowLeft className="h-5 w-5 mr-2" />
                Back to Analysis
              </button>
              <div className="flex items-center space-x-2">
                <MapPin className="h-6 w-6 text-blue-600" />
                <h1 className="text-2xl font-bold text-gray-900">Singapore TCO Test</h1>
              </div>
            </div>
            <button
              onClick={exportToCSV}
              className="flex items-center bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </button>
          </div>
          
          {/* TCO Parameters Display */}
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center mb-2">
              <Calculator className="h-5 w-5 text-blue-600 mr-2" />
              <h3 className="font-semibold text-blue-800">TCO Parameters (Hardcoded for Testing)</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-blue-700">Region:</span> Singapore (ap-southeast-1)
              </div>
              <div>
                <span className="font-medium text-blue-700">Production:</span> Reserved Instance (3 Year, No Upfront)
              </div>
              <div>
                <span className="font-medium text-blue-700">Non-Production:</span> On-Demand (50% utilization)
              </div>
              <div>
                <span className="font-medium text-blue-700">Total VMs:</span> {vmCosts.length}
              </div>
            </div>
          </div>
        </div>

        {/* Cost Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Monthly Cost</h3>
            <p className="text-3xl font-bold text-blue-600">${totalMonthlyCost.toFixed(2)}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Annual Cost</h3>
            <p className="text-3xl font-bold text-green-600">${totalAnnualCost.toFixed(2)}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Average Cost per VM</h3>
            <p className="text-3xl font-bold text-purple-600">
              ${vmCosts.length > 0 ? (totalMonthlyCost / vmCosts.length).toFixed(2) : '0.00'}
            </p>
          </div>
        </div>

        {/* VM Costs Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">VM Cost Analysis</h3>
            <p className="text-sm text-gray-600 mt-1">
              Detailed cost breakdown for each VM using Singapore region pricing
            </p>
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    VM Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Instance Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Environment
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    CPU/Memory/Storage
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Instance Cost
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Storage Cost
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Monthly
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Pricing Plan
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {vmCosts.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-6 py-12 text-center">
                      <div className="text-gray-500">
                        <div className="text-lg font-medium mb-2">No VM data found</div>
                        <div className="text-sm mb-4">
                          This could happen if:
                          <ul className="mt-2 text-left inline-block">
                            <li>• The session doesn't exist or has expired</li>
                            <li>• No RVTools data has been uploaded for this session</li>
                            <li>• All VMs were filtered out during processing</li>
                          </ul>
                        </div>
                        <button
                          onClick={() => navigate('/dashboard')}
                          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                        >
                          Go to Dashboard & Upload RVTools Data
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  vmCosts.map((vm, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {vm.vmName}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {vm.recommendedInstanceType}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          vm.environment === 'Production' 
                            ? 'bg-red-100 text-red-800' 
                            : 'bg-blue-100 text-blue-800'
                        }`}>
                          {vm.environment}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {vm.cpuCores}C / {vm.memoryGB}GB / {vm.storageGB.toFixed(1)}GB
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                        ${vm.instanceCost.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${vm.storageCost.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-bold">
                        ${vm.totalMonthlyCost.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          vm.pricingPlan.includes('Reserved') 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {vm.pricingPlan}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Consistency Check */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Consistency Check</h3>
          <div className="space-y-4">
            {(() => {
              const groups: { [key: string]: VMCostData[] } = {};
              vmCosts.forEach(vm => {
                const key = `${vm.recommendedInstanceType}_${vm.environment}`;
                if (!groups[key]) groups[key] = [];
                groups[key].push(vm);
              });

              return Object.entries(groups).map(([key, vms]) => {
                const [instanceType, environment] = key.split('_');
                const instanceCosts = vms.map(vm => vm.instanceCost);
                const isConsistent = new Set(instanceCosts.map(cost => cost.toFixed(2))).size === 1;
                
                return (
                  <div key={key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <span className="font-medium">{instanceType}</span>
                      <span className="text-gray-500 ml-2">({environment})</span>
                      <span className="text-gray-400 ml-2">- {vms.length} VM(s)</span>
                    </div>
                    <div className="flex items-center">
                      {isConsistent ? (
                        <span className="flex items-center text-green-600">
                          <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                          Consistent (${instanceCosts[0].toFixed(2)})
                        </span>
                      ) : (
                        <span className="flex items-center text-red-600">
                          <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
                          Inconsistent ({instanceCosts.map(c => `$${c.toFixed(2)}`).join(', ')})
                        </span>
                      )}
                    </div>
                  </div>
                );
              });
            })()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SingaporeTCOTest;
