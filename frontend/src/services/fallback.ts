/**
 * Fallback data and functions for when the backend is unavailable
 * This allows the application to work in demo mode even when the backend is down
 */

import { AnalysisPhase } from '../types';

// Generate a unique session ID
export const generateSessionId = () => `fallback-${Date.now()}`;

// Create a fallback session
export const createFallbackSession = (vmInventory: any[]) => {
  const sessionId = generateSessionId();
  return {
    session_id: sessionId,
    status: 'completed',
    current_phase: AnalysisPhase.MIGRATION_SCOPE,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    vm_count: vmInventory.length,
    vm_inventory: vmInventory,
    completed_phases: [
      AnalysisPhase.MIGRATION_SCOPE,
      AnalysisPhase.COST_ESTIMATES,
      AnalysisPhase.MODERNIZATION,
      AnalysisPhase.REPORT_GENERATION
    ],
    analysis_results: generateFallbackAnalysisResults(vmInventory)
  };
};

// Generate fallback analysis results
export const generateFallbackAnalysisResults = (vmInventory: any[]) => {
  const vmCount = vmInventory.length;
  
  return {
    analysis_id: `fallback_${Date.now()}`,
    current_cost: vmCount * 150,
    projected_aws_cost: vmCount * 100,
    estimated_savings: vmCount * 50,
    savings_percentage: 33,
    migration_blockers: generateFallbackBlockers(vmInventory),
    workload_classifications: generateFallbackClassifications(vmInventory),
    instance_recommendations: generateFallbackRecommendations(vmInventory),
    modernization_opportunities: generateFallbackOpportunities(vmInventory),
    recommendations: generateFallbackRecommendations(vmInventory),
    migration_complexity: vmCount > 50 ? 'High' : vmCount > 20 ? 'Medium' : 'Low',
    timeline_months: vmCount > 50 ? 12 : vmCount > 20 ? 6 : 3
  };
};

// Generate fallback migration blockers
export const generateFallbackBlockers = (vmInventory: any[]) => {
  const blockers = [];
  const blockerCount = Math.min(5, Math.max(1, Math.floor(vmInventory.length / 20)));
  
  for (let i = 0; i < blockerCount; i++) {
    const vm = vmInventory[i] || { vm_name: `VM-${i+1}` };
    blockers.push({
      vm_name: vm.vm_name,
      blocker_type: ['OS_COMPATIBILITY', 'HARDWARE_DEPENDENCY', 'LICENSING_ISSUE'][i % 3],
      severity: ['HIGH', 'MEDIUM', 'LOW'][i % 3],
      issue: `Sample migration issue for ${vm.vm_name}`,
      remediation: 'This is a fallback recommendation for demonstration purposes',
      confidence_score: 0.8
    });
  }
  
  return blockers;
};

// Generate fallback workload classifications
export const generateFallbackClassifications = (vmInventory: any[]) => {
  const classifications = [];
  const vmCount = vmInventory.length;
  
  classifications.push({
    vm_name: vmInventory[0]?.vm_name || 'VM-1',
    classification: 'PRODUCTION',
    confidence_score: 0.9,
    reasoning: 'Production classification based on resource allocation',
    pricing_model: 'RESERVED_INSTANCE'
  });
  
  if (vmCount > 1) {
    classifications.push({
      vm_name: vmInventory[1]?.vm_name || 'VM-2',
      classification: 'DEVELOPMENT',
      confidence_score: 0.85,
      reasoning: 'Development classification based on naming convention',
      pricing_model: 'ON_DEMAND'
    });
  }
  
  if (vmCount > 2) {
    classifications.push({
      vm_name: vmInventory[2]?.vm_name || 'VM-3',
      classification: 'TEST',
      confidence_score: 0.8,
      reasoning: 'Test classification based on resource allocation',
      pricing_model: 'ON_DEMAND'
    });
  }
  
  return classifications;
};

// Generate fallback instance recommendations
export const generateFallbackRecommendations = (vmInventory: any[]) => {
  const recommendations = [];
  const recommendationCount = Math.min(5, vmInventory.length);
  
  for (let i = 0; i < recommendationCount; i++) {
    const vm = vmInventory[i] || { vm_name: `VM-${i+1}`, cpu_count: 2, memory_mb: 4096 };
    const cpuCount = vm.cpu_count || 2;
    const memoryGB = (vm.memory_mb || 4096) / 1024;
    
    let instanceType = 't3.medium';
    let monthlyCost = 35;
    
    if (cpuCount >= 8 || memoryGB >= 32) {
      instanceType = 'm5.4xlarge';
      monthlyCost = 280;
    } else if (cpuCount >= 4 || memoryGB >= 16) {
      instanceType = 'm5.2xlarge';
      monthlyCost = 140;
    } else if (cpuCount >= 2 || memoryGB >= 8) {
      instanceType = 'm5.large';
      monthlyCost = 70;
    }
    
    const currentCost = Math.max(50, cpuCount * 15 + memoryGB * 8);
    const savings = Math.max(0, currentCost - monthlyCost);
    
    recommendations.push({
      vm_name: vm.vm_name,
      current_specs: `${cpuCount} vCPU, ${memoryGB.toFixed(1)}GB RAM`,
      recommended_instance: instanceType,
      reasoning: 'Fallback recommendation based on VM specifications',
      alternatives: ['t3.large', 'm5.large'],
      monthly_cost_current: currentCost,
      monthly_cost_recommended: monthlyCost,
      estimated_savings: savings
    });
  }
  
  return recommendations;
};

// Generate fallback modernization opportunities
export const generateFallbackOpportunities = (vmInventory: any[]) => {
  const opportunities = [];
  const opportunityCount = Math.min(3, vmInventory.length);
  
  const opportunityTypes = [
    'CONTAINERIZATION',
    'SERVERLESS',
    'MANAGED_DATABASE',
    'OS_UPGRADE'
  ];
  
  const awsServices = [
    'ECS Fargate',
    'Lambda',
    'RDS',
    'EC2'
  ];
  
  for (let i = 0; i < opportunityCount; i++) {
    const vm = vmInventory[i] || { vm_name: `VM-${i+1}` };
    const opportunityType = opportunityTypes[i % opportunityTypes.length];
    const awsService = awsServices[i % awsServices.length];
    
    opportunities.push({
      vm_name: vm.vm_name,
      opportunity_type: opportunityType,
      aws_service: awsService,
      complexity: ['LOW', 'MEDIUM', 'HIGH'][i % 3],
      estimated_savings: 100 + (i * 50),
      implementation_timeline: '3-6 months',
      description: `Fallback modernization opportunity for ${vm.vm_name}`
    });
  }
  
  return opportunities;
};

// Generate fallback cost estimates analysis
export const generateFallbackCostEstimates = (sessionId: string, vmInventory: any[]) => {
  const vmCount = vmInventory.length;
  const avgCostPerVM = 100;
  const totalMonthlyCost = vmCount * avgCostPerVM;
  
  return {
    session_id: sessionId,
    current_monthly_cost: totalMonthlyCost * 1.3, // 30% higher than AWS
    projected_aws_cost: totalMonthlyCost,
    estimated_savings: totalMonthlyCost * 0.3,
    savings_percentage: 30,
    analysis_complete: true,
    cost_breakdown: {
      compute: totalMonthlyCost * 0.6,
      storage: totalMonthlyCost * 0.3,
      network: totalMonthlyCost * 0.1
    },
    vm_cost_estimates: vmInventory.slice(0, 5).map((vm, i) => ({
      vm_name: vm.vm_name || `VM-${i+1}`,
      current_monthly_cost: 130 + (i * 10),
      projected_monthly_cost: 100 + (i * 7),
      savings_percentage: 30,
      instance_type: 'm5.large',
      storage_gb: 50
    }))
  };
};

// Generate fallback modernization analysis
export const generateFallbackModernization = (sessionId: string, vmInventory: any[]) => {
  const vmCount = vmInventory.length;
  const opportunityCount = Math.min(5, vmCount);
  
  return {
    session_id: sessionId,
    total_opportunities: opportunityCount,
    estimated_savings: opportunityCount * 1000,
    analysis_complete: true,
    opportunities: generateFallbackOpportunities(vmInventory),
    summary: {
      containerization_candidates: Math.ceil(opportunityCount / 3),
      serverless_candidates: Math.floor(opportunityCount / 3),
      managed_service_candidates: Math.floor(opportunityCount / 3),
      total_potential_savings: opportunityCount * 1000
    }
  };
};

// Generate fallback migration scope analysis
export const generateFallbackMigrationScope = (sessionId: string, vmInventory: any[]) => {
  const vmCount = vmInventory.length;
  const blockerCount = Math.min(5, Math.max(1, Math.floor(vmCount / 20)));
  
  return {
    session_id: sessionId,
    total_vms: vmCount,
    migration_ready: vmCount - blockerCount,
    blockers_found: blockerCount,
    analysis_complete: true,
    blockers: generateFallbackBlockers(vmInventory),
    summary: {
      ready_percentage: Math.round(((vmCount - blockerCount) / vmCount) * 100),
      critical_blockers: Math.ceil(blockerCount / 3),
      warning_blockers: Math.floor(blockerCount / 3),
      info_blockers: Math.floor(blockerCount / 3)
    }
  };
};
