import axios, { AxiosInstance, AxiosResponse } from 'axios';
import {
  AnalysisPhase,
  AnalysisSession,
  SessionStatusResponse,
  PhaseAdvanceResponse,
  MigrationScopeAnalysis,
  CostEstimatesAnalysis,
  ModernizationAnalysis,
  TCOParameters,
  PaginatedResponse,
  MigrationBlocker,
  VMCostEstimate,
  ModernizationOpportunity,
  FilterOptions,
  ErrorResponse,
} from '../types';

class ApiService {
  private api: AxiosInstance;
  private retryCount: number = 0;
  private maxRetries: number = 3;

  constructor() {
    // Use environment variable for API base URL, with fallback logic
    const envApiUrl = import.meta.env.VITE_API_BASE_URL;
    const hostname = window.location.hostname;
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
    
    let apiBaseUrl: string;
    
    if (envApiUrl) {
      // Use environment-configured API URL (production/staging)
      apiBaseUrl = envApiUrl.endsWith('/api') ? envApiUrl : `${envApiUrl}/api`;
    } else if (isLocalhost) {
      // Fallback: Accessed via localhost - use localhost backend
      apiBaseUrl = 'http://localhost:8000/api';
    } else {
      // Fallback: Accessed via network IP - use network IP for backend
      apiBaseUrl = `http://${hostname}:8000/api`;
    }
    
    const isLocalTesting = !envApiUrl || envApiUrl.includes('localhost') || envApiUrl.includes('127.0.0.1');
    
    console.log('API Service initialized with base URL:', apiBaseUrl);
    console.log('Environment API URL:', envApiUrl);
    console.log('Local testing mode:', isLocalTesting);
    console.log('Frontend hostname:', hostname);
    
    this.api = axios.create({
      baseURL: apiBaseUrl,
      timeout: 60000, // Increased timeout to 60 seconds for large file uploads
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor with retry logic
    this.api.interceptors.response.use(
      (response) => {
        // Reset retry count on successful response
        this.retryCount = 0;
        return response;
      },
      async (error) => {
        // Implement retry logic for network errors or 5xx server errors
        if (
          (error.code === 'ECONNABORTED' || 
           error.code === 'ERR_NETWORK' || 
           (error.response && error.response.status >= 500)) && 
          this.retryCount < this.maxRetries
        ) {
          this.retryCount++;
          console.log(`Retrying API request (${this.retryCount}/${this.maxRetries})...`);
          
          // Exponential backoff
          const delay = Math.pow(2, this.retryCount) * 1000;
          await new Promise(resolve => setTimeout(resolve, delay));
          
          // Return the original request with increased timeout
          const originalRequest = error.config;
          originalRequest.timeout = originalRequest.timeout * 1.5; // Increase timeout for retry
          return this.api(originalRequest);
        }
        
        // Reset retry count if we're not retrying
        this.retryCount = 0;
        
        return Promise.reject(this.handleError(error));
      }
    );
  }

  private handleError(error: any): ErrorResponse {
    if (error.response) {
      // Server responded with error status
      return {
        error: error.response.data?.error || 'Server Error',
        message: error.response.data?.message || 'An error occurred',
        details: error.response.data?.details,
        timestamp: new Date().toISOString(),
      };
    } else if (error.request) {
      // Request made but no response
      return {
        error: 'Network Error',
        message: 'Unable to connect to AWS backend server. Please check your network connection and try again.',
        timestamp: new Date().toISOString(),
      };
    } else {
      // Something else happened
      return {
        error: 'Unknown Error',
        message: error.message || 'An unexpected error occurred',
        timestamp: new Date().toISOString(),
      };
    }
  }

  // ============================================================================
  // FILE UPLOAD
  // ============================================================================

  async uploadRVToolsFile(file: File): Promise<{ success: boolean; vm_inventory: any[]; total_vms: number }> {
    try {
      console.log('Uploading RVTools file directly to backend:', {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type
      });
      
      // PRIMARY APPROACH: Use direct file upload to backend
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        // Use direct file upload endpoint - this ensures backend processes raw RVTools data
        const uploadResponse = await axios.post(
          `${this.api.defaults.baseURL}/upload-rvtools`, 
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
            timeout: 120000, // 2 minutes timeout for large files
          }
        );
        
        console.log('Direct upload successful:', uploadResponse.data);
        
        // Extract VM inventory from backend response
        const vmInventory = uploadResponse.data.vm_inventory || [];
        
        if (vmInventory.length === 0) {
          throw new Error('No VM data found in uploaded file');
        }
        
        console.log('Backend processed VM inventory:', {
          count: vmInventory.length,
          sample: vmInventory[0]
        });
        
        return {
          success: true,
          vm_inventory: vmInventory,
          total_vms: vmInventory.length
        };
        
      } catch (directUploadError) {
        console.error('Direct upload failed, trying client-side parsing fallback:', directUploadError);
        
        // FALLBACK APPROACH: Client-side parsing (only if direct upload fails)
        try {
          // Parse Excel file client-side as fallback
          const vmInventory = await this.parseRVToolsFile(file);
          
          console.log('Client-side parsing fallback successful:', {
            count: vmInventory.length,
            sample: vmInventory[0]
          });
          
          // Call the correct endpoint to start analysis session
          const response: AxiosResponse = await this.api.post('/phases/start-analysis', {
            vm_inventory: vmInventory,
            migration_timeline: '12_months',
            optimization_level: 'balanced'
          });

          console.log('Fallback API response:', response.data);

          return {
            success: true,
            vm_inventory: vmInventory,
            total_vms: vmInventory.length
          };
          
        } catch (fallbackError) {
          console.error('Both direct upload and fallback failed:', fallbackError);
          throw directUploadError; // Throw the original direct upload error
        }
      }
    } catch (error: any) {
      console.error('Failed to process RVTools file:', error);
      throw error;
    }
  }

  // Helper function to parse RVTools Excel file client-side
  private async parseRVToolsFile(file: File): Promise<any[]> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (e) => {
        try {
          // Import xlsx library dynamically
          import('xlsx').then((XLSX) => {
            const data = new Uint8Array(e.target?.result as ArrayBuffer);
            const workbook = XLSX.read(data, { type: 'array' });
            
            // Look for vInfo sheet (standard RVTools sheet name)
            const sheetName = workbook.SheetNames.find(name => 
              name.toLowerCase().includes('vinfo') || 
              name.toLowerCase().includes('vm') ||
              name.toLowerCase().includes('virtual')
            ) || workbook.SheetNames[0]; // fallback to first sheet
            
            if (!sheetName) {
              reject(new Error('No valid sheet found in Excel file'));
              return;
            }
            
            const worksheet = workbook.Sheets[sheetName];
            const jsonData = XLSX.utils.sheet_to_json(worksheet);
            
            console.log(`Found ${jsonData.length} rows in sheet "${sheetName}"`);
            console.log('Sample row:', jsonData[0]);
            
            // Convert Excel data to VM inventory format with validation
            const vmInventory = jsonData
              .filter((row: any) => {
                // Filter out empty rows or rows without VM name
                const vmName = row['VM'] || row['Name'] || row['VM Name'] || row['Virtual Machine'];
                return vmName && vmName.toString().trim().length > 0;
              })
              .map((row: any, index: number) => {
                // Helper function to safely parse numbers
                const parseNumber = (value: any, defaultValue: number): number => {
                  if (value === null || value === undefined || value === '') return defaultValue;
                  const parsed = parseInt(String(value).replace(/[^0-9.-]/g, ''));
                  return isNaN(parsed) ? defaultValue : Math.max(0, parsed);
                };

                // Helper function to safely parse strings
                const parseString = (value: any, defaultValue: string): string => {
                  if (value === null || value === undefined) return defaultValue;
                  return String(value).trim() || defaultValue;
                };

                // Extract VM name from various possible column names
                const vmName = parseString(
                  row['VM'] || row['Name'] || row['VM Name'] || row['Virtual Machine'], 
                  `VM-${index + 1}`
                );

                // Extract CPU count from various possible column names
                const cpuCount = parseNumber(
                  row['CPUs'] || row['CPU'] || row['vCPU'] || row['Num CPUs'] || row['CPU Count'], 
                  2
                );

                // Extract memory from various possible column names (convert to MB if needed)
                let memoryMB = parseNumber(
                  row['Memory'] || row['RAM'] || row['Memory MB'] || row['Memory (MB)'] || row['Configured Memory (MB)'], 
                  4096
                );
                
                // If memory seems to be in GB, convert to MB
                if (memoryMB < 100) {
                  memoryMB = memoryMB * 1024;
                }

                // Extract disk size from RVTools storage columns (prioritize consumed storage)
                // RVTools provides storage in MiB, need to convert to GB
                let diskGB = 0;
                
                // Try to get consumed storage first (In Use MiB)
                const consumedStorageMiB = parseNumber(row['In Use MiB'], 0);
                
                // Fallback to provisioned storage (Provisioned MiB)
                const provisionedStorageMiB = parseNumber(row['Provisioned MiB'], 0);
                
                // Use consumed storage if available, otherwise use provisioned
                let storageMiB = 0;
                if (consumedStorageMiB > 0) {
                  storageMiB = consumedStorageMiB;
                } else if (provisionedStorageMiB > 0) {
                  storageMiB = provisionedStorageMiB;
                } else {
                  // Fallback to other possible column names
                  storageMiB = parseNumber(
                    row['Total disk capacity MiB'] || row['Disk'] || row['Storage'] || row['Provisioned Space (MB)'] || row['Used Space (MB)'], 
                    51200  // Default 50GB in MiB (50 * 1024)
                  );
                }
                
                // Convert MiB to GB: 1 MiB = 1.048576 MB, 1 GB = 1024 MB
                if (storageMiB > 0) {
                  diskGB = Math.round((storageMiB * 1.048576) / 1024 * 100) / 100; // Round to 2 decimal places
                } else {
                  diskGB = 50; // Default 50GB instead of 100GB
                }

                // Extract OS type from various possible column names
                const osType = parseString(
                  row['OS'] || row['Guest OS'] || row['Operating System'] || row['Guest OS Full Name'] || row['OS according to the configuration file'], 
                  'Unknown'
                );

                // Extract power state
                const powerState = parseString(
                  row['Powerstate'] || row['Power State'] || row['State'], 
                  'poweredOn'
                );
                
                // Extract creation date from various possible column names
                const creationDate = row['Creation date'] || row['Created'] || row['Creation Date'] || row['Created Date'];
                
                // Create clean VM object with only valid, required fields
                const vmData = {
                  vm_name: vmName,
                  cpu_count: cpuCount,
                  memory_mb: memoryMB,
                  disk_gb: diskGB,
                  os_type: osType,
                  power_state: powerState,
                  host: parseString(row['Host'] || row['ESX Host'] || row['ESX Server'], 'Unknown'),
                  cluster: parseString(row['Cluster'] || row['Cluster Name'], 'Unknown'),
                  datacenter: parseString(row['Datacenter'] || row['Datacenter Name'], 'Unknown'),
                  creation_date: creationDate ? new Date(creationDate).toISOString() : null
                };

                // Validate the VM data with reasonable defaults
                if (vmData.cpu_count < 1 || vmData.cpu_count > 128) vmData.cpu_count = 2;
                if (vmData.memory_mb < 512 || vmData.memory_mb > 1048576) vmData.memory_mb = 4096;
                if (vmData.disk_gb < 1 || vmData.disk_gb > 16384) vmData.disk_gb = 50; // Use 50GB instead of 100GB

                return vmData;
              });
            
            console.log(`Parsed ${vmInventory.length} valid VMs from RVTools file`);
            
            if (vmInventory.length === 0) {
              reject(new Error('No valid VM data found in Excel file. Please check the file format.'));
              return;
            }
            
            resolve(vmInventory);
          }).catch(err => {
            console.error('Error loading XLSX library:', err);
            reject(new Error('Failed to load Excel processing library. Please try again.'));
          });
        } catch (error) {
          console.error('Error parsing Excel file:', error);
          reject(error);
        }
      };
      
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsArrayBuffer(file);
    });
  }

  // ============================================================================
  // GENERIC HTTP METHODS
  // ============================================================================

  async get(url: string): Promise<any> {
    try {
      const response: AxiosResponse = await this.api.get(url);
      return response;
    } catch (error) {
      console.error(`GET ${url} failed:`, error);
      throw error;
    }
  }

  async post(url: string, data?: any): Promise<any> {
    try {
      const response: AxiosResponse = await this.api.post(url, data);
      return response;
    } catch (error) {
      console.error(`POST ${url} failed:`, error);
      throw error;
    }
  }

  async put(url: string, data?: any): Promise<any> {
    try {
      const response: AxiosResponse = await this.api.put(url, data);
      return response;
    } catch (error) {
      console.error(`PUT ${url} failed:`, error);
      throw error;
    }
  }

  // ============================================================================
  // SESSION MANAGEMENT
  // ============================================================================

  async createSession(vmInventory: any[]): Promise<AnalysisSession> {
    try {
      console.log('Creating analysis session with VM inventory:', vmInventory.length, 'VMs');
      
      // Call the correct endpoint to start analysis session with proper data structure
      const requestData = {
        vm_inventory: vmInventory
      };
      
      const response: AxiosResponse = await this.api.post('/phases/start-analysis', requestData);
      
      console.log('Session creation response:', response.data);
      
      // Extract session data from response
      const sessionData = response.data;
      
      // Create session object
      const session = {
        session_id: sessionData.session_id || `session-${Date.now()}-${Math.random().toString(36).substring(2, 10)}`,
        status: sessionData.status || 'active',
        current_phase: sessionData.current_phase || AnalysisPhase.MIGRATION_SCOPE,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        vm_count: vmInventory.length,
        vm_inventory: vmInventory,
        completed_phases: [
          AnalysisPhase.MIGRATION_SCOPE,
          AnalysisPhase.COST_ESTIMATES,
          AnalysisPhase.MODERNIZATION,
          AnalysisPhase.REPORT_GENERATION
        ], // All phases completed and accessible
        analysis_results: response.data
      };
      
      // Store session in localStorage for persistence
      localStorage.setItem(`session_${session.session_id}`, JSON.stringify(session));
      localStorage.setItem('currentSession', JSON.stringify(session));
      localStorage.setItem('currentSessionId', session.session_id);
      
      return session;
    } catch (error) {
      console.error('Error creating session:', error);
      throw error; // Propagate the error to be handled by the caller
    }
  }

  async getSession(sessionId: string): Promise<SessionStatusResponse> {
    // For direct analysis, return completed status
    return {
      session_id: sessionId,
      current_phase: AnalysisPhase.MIGRATION_SCOPE, // Start with first phase for user navigation
      completed_phases: [
        AnalysisPhase.MIGRATION_SCOPE,
        AnalysisPhase.COST_ESTIMATES,
        AnalysisPhase.MODERNIZATION,
        AnalysisPhase.REPORT_GENERATION
      ], // All phases completed and accessible
      total_vms: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
  }

  async listSessions(): Promise<SessionStatusResponse[]> {
    // Direct analysis doesn't store sessions, return empty array
    return [];
  }

  async deleteSession(sessionId: string): Promise<{ success: boolean; message: string }> {
    // Direct analysis doesn't store sessions
    return { success: true, message: 'Session deleted (direct analysis mode)' };
  }

  async advancePhase(sessionId: string): Promise<PhaseAdvanceResponse> {
    // Direct analysis completes all phases immediately
    return {
      session_id: sessionId,
      previous_phase: AnalysisPhase.MIGRATION_SCOPE,
      current_phase: AnalysisPhase.COST_ESTIMATES,
      status: 'completed',
      message: 'Phase advanced successfully'
    };
  }

  // ============================================================================
  // MIGRATION SCOPE ANALYSIS
  // ============================================================================

  async analyzeMigrationScope(sessionId: string): Promise<MigrationScopeAnalysis> {
    try {
      // For direct analysis, extract from session data
      const session = await this.getSession(sessionId);
      
      // Make API call to get migration scope analysis
      const response: AxiosResponse = await this.api.get(`/migration-scope/${sessionId}`);
      
      return response.data;
    } catch (error) {
      console.error('Error analyzing migration scope:', error);
      throw error;
    }
  }

  async getMigrationBlockers(
    sessionId: string,
    filters: FilterOptions = {}
  ): Promise<PaginatedResponse<MigrationBlocker>> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString());
      }
    });

    const response: AxiosResponse<PaginatedResponse<MigrationBlocker>> = await this.api.get(
      `/migration-scope/blockers/${sessionId}?${params}`
    );
    return response.data;
  }

  async getMigrationScopeSummary(sessionId: string): Promise<any> {
    const response: AxiosResponse = await this.api.get(`/migration-scope/summary/${sessionId}`);
    return response.data;
  }

  async getWorkloadClassifications(sessionId: string): Promise<any> {
    const response: AxiosResponse = await this.api.get(`/migration-scope/workload-classifications/${sessionId}`);
    return response.data;
  }

  async getInfrastructureInsights(sessionId: string): Promise<any> {
    const response: AxiosResponse = await this.api.get(`/migration-scope/infrastructure-insights/${sessionId}`);
    return response.data;
  }

  async exportMigrationScope(sessionId: string, format: 'json' | 'csv' = 'json'): Promise<any> {
    const response: AxiosResponse = await this.api.get(`/migration-scope/export/${sessionId}?format=${format}`);
    return response.data;
  }

  // ============================================================================
  // COST ESTIMATES
  // ============================================================================

  async analyzeCostEstimates(sessionId: string, tcoParameters?: TCOParameters): Promise<CostEstimatesAnalysis> {
    try {
      console.log('Calling backend cost estimates analysis with real AWS pricing...');
      console.log('Session ID:', sessionId);
      console.log('TCO Parameters:', tcoParameters);
      
      // Call the backend API endpoint that uses real AWS pricing
      const response: AxiosResponse = await this.api.post(
        `/cost-estimates/analyze/${sessionId}`,
        tcoParameters || {}
      );
      
      console.log('Backend cost analysis response:', response.data);
      return response.data;
    } catch (error) {
      console.error('Error analyzing cost estimates with backend:', error);
      throw error;
    }
  }

  async getDetailedCostEstimates(
    sessionId: string,
    filters: FilterOptions = {}
  ): Promise<PaginatedResponse<VMCostEstimate>> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString());
      }
    });

    const response: AxiosResponse<PaginatedResponse<VMCostEstimate>> = await this.api.get(
      `/cost-estimates/detailed/${sessionId}?${params}`
    );
    return response.data;
  }

  async getCostSummary(sessionId: string): Promise<any> {
    const response: AxiosResponse = await this.api.get(`/cost-estimates/summary/${sessionId}`);
    return response.data;
  }

  async updateTCOParameters(sessionId: string, tcoParameters: TCOParameters): Promise<CostEstimatesAnalysis> {
    const response: AxiosResponse<CostEstimatesAnalysis> = await this.api.put(
      `/cost-estimates/parameters/${sessionId}`,
      tcoParameters
    );
    return response.data;
  }

  async exportCostEstimates(sessionId: string, format: 'json' | 'csv' = 'json'): Promise<any> {
    const response: AxiosResponse = await this.api.get(`/cost-estimates/export/${sessionId}?format=${format}`);
    return response.data;
  }

  async getPricingInfo(region: string, instanceTypes?: string): Promise<any> {
    const params = instanceTypes ? `?instance_types=${instanceTypes}` : '';
    const response: AxiosResponse = await this.api.get(`/cost-estimates/pricing-info/${region}${params}`);
    return response.data;
  }

  // ============================================================================
  // MODERNIZATION
  // ============================================================================

  async analyzeModernization(sessionId: string): Promise<ModernizationAnalysis> {
    try {
      // Try multiple approaches to get the VM inventory data
      let vmInventory = [];
      
      // Approach 1: Try to get the session data from localStorage with session_ prefix
      const sessionData = localStorage.getItem(`session_${sessionId}`);
      if (sessionData) {
        const parsedSession = JSON.parse(sessionData);
        vmInventory = parsedSession.vm_inventory || [];
      }
      
      // Approach 2: Try to get the current session from localStorage
      if (vmInventory.length === 0) {
        const currentSessionId = localStorage.getItem('currentSessionId');
        if (currentSessionId === sessionId) {
          const currentSessionData = localStorage.getItem('currentSession');
          if (currentSessionData) {
            const parsedCurrentSession = JSON.parse(currentSessionData);
            vmInventory = parsedCurrentSession.vm_inventory || [];
          }
        }
      }
      
      // Approach 3: Try to get all sessions from localStorage and find the matching one
      if (vmInventory.length === 0) {
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key && (key.includes(sessionId) || key.includes('session'))) {
            try {
              const data = localStorage.getItem(key);
              if (data) {
                const parsedData = JSON.parse(data);
                if (parsedData.session_id === sessionId && parsedData.vm_inventory) {
                  vmInventory = parsedData.vm_inventory;
                  break;
                }
              }
            } catch (e) {
              console.error('Error parsing localStorage data:', e);
            }
          }
        }
      }
      
      // If we still don't have VM inventory data, try to get it from the API
      if (vmInventory.length === 0) {
        try {
          // Make a direct API call to get session data
          const response = await this.api.get(`/sessions/${sessionId}`);
          if (response.data && response.data.vm_inventory) {
            vmInventory = response.data.vm_inventory;
          }
        } catch (e) {
          console.error('Error getting session data from API:', e);
        }
      }
      
      // If we still don't have VM inventory data, we can't proceed
      if (vmInventory.length === 0) {
        throw new Error("No VM inventory data available. Please upload RVTools data first.");
      }
      
      // Make an API call to start analysis session for modernization
      const requestData = {
        vm_inventory: vmInventory
      };
      const response = await this.api.post('/phases/start-analysis', requestData);
      
      const tcoData = response.data;
      
      // Filter out OS upgrade opportunities
      const filteredOpportunities = tcoData.modernization_opportunities?.filter(opportunity => {
        // Filter out opportunities with OS upgrade in the type, description, or target service
        return !(
          opportunity.opportunity_type?.toLowerCase().includes('os') || 
          opportunity.opportunity_type?.toLowerCase().includes('upgrade') ||
          opportunity.aws_service?.toLowerCase().includes('os') ||
          (opportunity.description && opportunity.description.toLowerCase().includes('os upgrade'))
        );
      }) || [];
      
      // Transform the API response to match the expected frontend structure
      const transformedOpportunities = filteredOpportunities.map((opportunity, index) => {
        // Calculate the current monthly cost based on estimated savings
        // Assuming the savings is approximately 30% of current cost
        const estimatedSavings = opportunity.estimated_savings || 0;
        const currentMonthlyCost = estimatedSavings > 0 ? Math.round(estimatedSavings / 0.3) : 100;
        const modernizedMonthlyCost = currentMonthlyCost - estimatedSavings;
        
        // Determine current workload type based on opportunity type
        let currentWorkloadType = 'Virtual Machine';
        if (opportunity.opportunity_type?.toLowerCase().includes('database')) {
          currentWorkloadType = 'Database Server';
        } else if (opportunity.vm_name?.toLowerCase().includes('web') || 
                  opportunity.description?.toLowerCase().includes('web')) {
          currentWorkloadType = 'Web Server';
        } else if (opportunity.vm_name?.toLowerCase().includes('app') || 
                  opportunity.description?.toLowerCase().includes('application')) {
          currentWorkloadType = 'Application Server';
        }
        
        // Generate benefits based on opportunity type
        const benefits = [];
        if (opportunity.opportunity_type?.toLowerCase().includes('database')) {
          benefits.push('Automated backups and maintenance');
          benefits.push('High availability and failover support');
          benefits.push('Reduced operational overhead');
        } else if (opportunity.opportunity_type?.toLowerCase().includes('container')) {
          benefits.push('Improved resource utilization');
          benefits.push('Simplified deployment process');
          benefits.push('Better scalability');
        } else if (opportunity.opportunity_type?.toLowerCase().includes('serverless')) {
          benefits.push('Pay only for what you use');
          benefits.push('Automatic scaling');
          benefits.push('No infrastructure management');
        } else {
          benefits.push('Reduced operational overhead');
          benefits.push('Improved reliability');
          benefits.push('Better performance');
        }
        
        // Map complexity to implementation_complexity
        let implementationComplexity = 'Medium';
        if (opportunity.complexity === 'LOW') {
          implementationComplexity = 'Low';
        } else if (opportunity.complexity === 'HIGH') {
          implementationComplexity = 'High';
        }
        
        // Return transformed opportunity
        return {
          id: `mod-${index + 1}`,
          vm_name: opportunity.vm_name,
          current_workload_type: currentWorkloadType,
          modernization_type: opportunity.opportunity_type?.toLowerCase(),
          target_aws_service: opportunity.aws_service,
          current_monthly_cost: currentMonthlyCost,
          modernized_monthly_cost: modernizedMonthlyCost,
          monthly_savings: opportunity.estimated_savings || 0,
          annual_savings: (opportunity.estimated_savings || 0) * 12,
          benefits: benefits,
          implementation_complexity: implementationComplexity
        };
      });
      
      // Recalculate summary metrics based on transformed opportunities
      const totalSavings = transformedOpportunities.reduce((sum, opp) => sum + (opp.monthly_savings || 0), 0);
      const avgSavingsPercentage = transformedOpportunities.length > 0 ? 
        transformedOpportunities.reduce((sum, opp) => {
          const currentCost = opp.current_monthly_cost || 0;
          const savings = opp.monthly_savings || 0;
          return sum + (currentCost > 0 ? (savings / currentCost) * 100 : 0);
        }, 0) / transformedOpportunities.length : 0;
      
      // Transform the data to match the expected ModernizationAnalysis structure
      return {
        session_id: sessionId,
        total_opportunities: transformedOpportunities.length,
        estimated_savings: totalSavings,
        analysis_complete: true,
        modernization_opportunities: transformedOpportunities,
        summary: {
          containerization_candidates: transformedOpportunities.filter(o => o.modernization_type?.includes('container')).length || 0,
          serverless_candidates: transformedOpportunities.filter(o => o.modernization_type?.includes('serverless')).length || 0,
          managed_service_candidates: transformedOpportunities.filter(o => 
            o.modernization_type?.includes('managed') || 
            o.modernization_type?.includes('database')
          ).length || 0,
          total_monthly_savings: totalSavings,
          average_savings_percentage: avgSavingsPercentage,
          total_potential_savings: totalSavings * 12
        }
      };
    } catch (error) {
      console.error('Modernization analysis failed:', error);
      throw new Error(`Modernization analysis failed: ${error.response?.data?.detail || error.message}`);
    }
  }

  async getModernizationOpportunities(
    sessionId: string,
    filters: FilterOptions = {}
  ): Promise<PaginatedResponse<ModernizationOpportunity>> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString());
      }
    });

    const response: AxiosResponse<PaginatedResponse<ModernizationOpportunity>> = await this.api.get(
      `/modernization/opportunities/${sessionId}?${params}`
    );
    return response.data;
  }

  async getModernizationSummary(sessionId: string): Promise<any> {
    const response: AxiosResponse = await this.api.get(`/modernization/summary/${sessionId}`);
    return response.data;
  }

  async getOpportunitiesByType(sessionId: string): Promise<Record<string, ModernizationOpportunity[]>> {
    const response: AxiosResponse<Record<string, ModernizationOpportunity[]>> = await this.api.get(
      `/modernization/opportunities-by-type/${sessionId}`
    );
    return response.data;
  }

  async exportModernizationAnalysis(sessionId: string, format: 'json' | 'csv' = 'json'): Promise<any> {
    const response: AxiosResponse = await this.api.get(`/modernization/export/${sessionId}?format=${format}`);
    return response.data;
  }

  // ============================================================================
  // HEALTH CHECKS
  // ============================================================================

  // ============================================================================
  // REPORT GENERATION
  // ============================================================================

  async downloadMigrationBlockerReport(sessionId: string): Promise<Blob> {
    try {
      const response: AxiosResponse<Blob> = await this.api.post(
        `/reports/migration-blockers/${sessionId}`,
        {},
        {
          responseType: 'blob',
          headers: {
            'Accept': 'application/pdf'
          }
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error downloading migration blocker report:', error);
      throw error;
    }
  }

  async downloadExecutiveSummaryReport(sessionId: string): Promise<Blob> {
    try {
      const response: AxiosResponse<Blob> = await this.api.post(
        `/reports/executive-summary/${sessionId}`,
        {},
        {
          responseType: 'blob',
          headers: {
            'Accept': 'application/pdf'
          }
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error downloading executive summary report:', error);
      throw error;
    }
  }

  async downloadTechnicalAnalysisReport(sessionId: string): Promise<Blob> {
    try {
      const response: AxiosResponse<Blob> = await this.api.post(
        `/reports/technical-analysis/${sessionId}`,
        {},
        {
          responseType: 'blob',
          headers: {
            'Accept': 'application/pdf'
          }
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error downloading technical analysis report:', error);
      throw error;
    }
  }

  async downloadMigrationRoadmapReport(sessionId: string): Promise<Blob> {
    try {
      const response: AxiosResponse<Blob> = await this.api.post(
        `/reports/migration-roadmap/${sessionId}`,
        {},
        {
          responseType: 'blob',
          headers: {
            'Accept': 'application/pdf'
          }
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error downloading migration roadmap report:', error);
      throw error;
    }
  }

  async getAvailableReports(sessionId: string): Promise<any> {
    try {
      const response: AxiosResponse = await this.api.get(`/reports/available/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting available reports:', error);
      throw error;
    }
  }

  // Helper method to download blob as file
  downloadBlobAsFile(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  // ============================================================================
  // HEALTH CHECK
  // ============================================================================

  async getHealthStatus(): Promise<any> {
    try {
      const response: AxiosResponse = await this.api.get('/health');
      return response.data;
    } catch (error) {
      return {
        status: 'error',
        timestamp: new Date().toISOString(),
        message: 'Unable to connect to AWS backend'
      };
    }
  }
}

// Create and export a singleton instance
const apiService = new ApiService();
export { apiService };
export default apiService;
