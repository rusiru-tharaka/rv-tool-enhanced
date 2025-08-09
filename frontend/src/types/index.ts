// Enhanced UX Frontend Types
// Matches the backend Pydantic models

export enum AnalysisPhase {
  MIGRATION_SCOPE = 'migration_scope',
  COST_ESTIMATES = 'cost_estimates',
  MODERNIZATION = 'modernization_opportunities',
  REPORT_GENERATION = 'implementation_roadmap',
}

export enum MigrationBlockerSeverity {
  CRITICAL = 'critical',
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
}

export enum ModernizationType {
  MANAGED_DATABASE = 'managed_database',
  SERVERLESS = 'serverless',
  CONTAINERIZATION = 'containerization',
  MANAGED_SERVICES = 'managed_services',
}

// Session Management
export interface AnalysisSession {
  session_id: string;
  user_id?: string;
  current_phase: AnalysisPhase;
  vm_inventory: VMData[];
  created_at: string;
  updated_at: string;
  completed_phases: AnalysisPhase[];
}

export interface PhaseProgress {
  phase: AnalysisPhase;
  completed: boolean;
  completion_percentage: number;
  data?: any;
}

// VM Data
export interface VMData {
  VM: string;
  CPUs: number;
  Memory: number; // MB
  'Provisioned MB': number;
  OS: string;
  [key: string]: any;
}

// Migration Scope
export interface MigrationBlocker {
  id: string;
  vm_name: string;
  severity: MigrationBlockerSeverity;
  issue_type: string;
  description: string;
  remediation: string;
  confidence_score: number;
}

export interface OutOfScopeItem {
  vm_name: string;
  reason: string;
  category: string;
  auto_detected: boolean;
}

export interface WorkloadClassification {
  classification: string;
  vm_count: number;
  percentage: number;
  vm_names: string[];
}

export interface InfrastructureInsights {
  total_vms: number;
  total_storage_tb: number;
  os_breakdown: Record<string, number>;
  prod_nonprod_ratio: Record<string, number>;
  average_vm_specs: Record<string, number>;
  total_resources: Record<string, number>;
}

export interface MigrationScopeAnalysis {
  session_id: string;
  total_vms: number;
  estimated_timeline_months: number;
  complexity_score: number;
  migration_blockers: MigrationBlocker[];
  out_of_scope_items: OutOfScopeItem[];
  workload_classifications: WorkloadClassification[];
  infrastructure_insights: InfrastructureInsights;
}

// Cost Estimates
export interface TCOParameters {
  target_region: string;
  production_ri_years: number;
  include_network: boolean;
  include_observability: boolean;
  network_cost_percentage: number;
  observability_cost_percentage: number;
}

export interface VMCostEstimate {
  vm_name: string;
  current_cpu: number;
  current_ram_gb: number;
  current_storage_gb: number;
  recommended_instance_family: string;
  recommended_instance_size: string;
  pricing_plan: string;
  ec2_monthly_cost: number;
  storage_monthly_cost: number;
  total_monthly_cost: number;
}

export interface CostSummary {
  infrastructure_monthly_cost: number;
  network_monthly_cost: number;
  observability_monthly_cost: number;
  total_monthly_cost: number;
  total_annual_cost: number;
}

export interface CostEstimatesAnalysis {
  session_id: string;
  tco_parameters: TCOParameters;
  cost_summary: CostSummary;
  detailed_estimates: VMCostEstimate[];
  total_vms_analyzed: number;
}

// Modernization
export interface ModernizationOpportunity {
  id: string;
  vm_name: string;
  current_workload_type: string;
  modernization_type: ModernizationType;
  target_aws_service: string;
  current_monthly_cost: number;
  modernized_monthly_cost: number;
  monthly_savings: number;
  annual_savings: number;
  benefits: string[];
  implementation_complexity: string;
}

export interface ModernizationCostImpact {
  current_aws_monthly_cost: number;
  modernized_aws_monthly_cost: number;
  total_monthly_savings: number;
  total_annual_savings: number;
  savings_percentage: number;
}

export interface ModernizationAnalysis {
  session_id: string;
  cost_impact: ModernizationCostImpact;
  opportunities: ModernizationOpportunity[];
  opportunities_by_type: Record<ModernizationType, ModernizationOpportunity[]>;
  total_opportunities: number;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SessionStatusResponse {
  session_id: string;
  current_phase: AnalysisPhase;
  completed_phases: AnalysisPhase[];
  total_vms: number;
  created_at: string;
  updated_at: string;
}

export interface PhaseAdvanceResponse {
  session_id: string;
  current_phase: AnalysisPhase;
  completed_phases: AnalysisPhase[];
  success: boolean;
  message: string;
}

export interface ErrorResponse {
  error: string;
  message: string;
  details?: any;
  timestamp: string;
}

// UI State Types
export interface LoadingState {
  isLoading: boolean;
  message?: string;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
  details?: any;
}

// Filter and Search Types
export interface FilterOptions {
  search?: string;
  severity?: MigrationBlockerSeverity;
  modernization_type?: ModernizationType;
  complexity?: string;
  min_savings?: number;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// Chart Data Types
export interface ChartDataPoint {
  name: string;
  value: number;
  color?: string;
}

export interface CostBreakdownData {
  category: string;
  current_cost: number;
  modernized_cost: number;
  savings: number;
}

// Navigation Types
export interface NavigationItem {
  phase: AnalysisPhase;
  title: string;
  description: string;
  completed: boolean;
  current: boolean;
  disabled: boolean;
}
