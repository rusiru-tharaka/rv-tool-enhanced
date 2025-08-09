  const analyzeMigrationScope = async (sessionId: string) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: { isLoading: true, message: 'Analyzing migration scope...' } });
      
      // For direct analysis, create migration scope analysis data from current session
      const currentSession = state.currentSession;
      if (!currentSession) {
        throw new Error('No active session found');
      }

      const vmInventory = currentSession.vm_inventory || [];
      
      // Analyze the real VM data to create meaningful insights
      const windowsVMs = vmInventory.filter(vm => 
        vm.os_type?.toLowerCase().includes('windows') || 
        vm.os_type?.toLowerCase().includes('microsoft')
      );
      const linuxVMs = vmInventory.filter(vm => 
        vm.os_type?.toLowerCase().includes('linux') || 
        vm.os_type?.toLowerCase().includes('ubuntu') || 
        vm.os_type?.toLowerCase().includes('centos') || 
        vm.os_type?.toLowerCase().includes('rhel')
      );
      const otherVMs = vmInventory.filter(vm => 
        !windowsVMs.includes(vm) && !linuxVMs.includes(vm)
      );

      // Calculate complexity based on real data
      const avgCpu = vmInventory.reduce((sum, vm) => sum + (vm.cpu_count || 2), 0) / vmInventory.length;
      const avgMemory = vmInventory.reduce((sum, vm) => sum + ((vm.memory_mb || 4096) / 1024), 0) / vmInventory.length;
      const complexityScore = Math.min(5, Math.max(1, 
        (avgCpu / 4) + (avgMemory / 8) + (vmInventory.length / 50)
      ));

      // Identify real migration blockers based on VM data
      const migrationBlockers = [];
      
      // Check for old Windows versions
      const oldWindowsVMs = vmInventory.filter(vm => 
        vm.os_type?.includes('2008') || vm.os_type?.includes('2003') || vm.os_type?.includes('XP')
      );
      if (oldWindowsVMs.length > 0) {
        migrationBlockers.push({
          id: 'legacy-windows',
          vm_name: oldWindowsVMs[0].vm_name,
          blocker_type: 'Legacy Windows OS',
          severity: 'high' as const,
          description: `${oldWindowsVMs.length} VM(s) running legacy Windows versions that may need updates`,
          recommendation: 'Upgrade to supported Windows versions before migration'
        });
      }

      // Check for high-resource VMs
      const highResourceVMs = vmInventory.filter(vm => 
        (vm.cpu_count || 0) > 16 || ((vm.memory_mb || 0) / 1024) > 64
      );
      if (highResourceVMs.length > 0) {
        migrationBlockers.push({
          id: 'high-resource',
          vm_name: highResourceVMs[0].vm_name,
          blocker_type: 'High Resource Requirements',
          severity: 'medium' as const,
          description: `${highResourceVMs.length} VM(s) with high CPU/memory requirements`,
          recommendation: 'Review instance sizing and consider reserved instances'
        });
      }

      // Check for powered-off VMs
      const poweredOffVMs = vmInventory.filter(vm => 
        vm.power_state?.toLowerCase() === 'poweredoff' || 
        vm.power_state?.toLowerCase() === 'suspended'
      );
      if (poweredOffVMs.length > 0) {
        migrationBlockers.push({
          id: 'powered-off',
          vm_name: poweredOffVMs[0].vm_name,
          blocker_type: 'Powered Off VMs',
          severity: 'low' as const,
          description: `${poweredOffVMs.length} VM(s) are powered off or suspended`,
          recommendation: 'Determine if these VMs are still needed before migration'
        });
      }

      // Identify out of scope items
      const outOfScopeItems = [];
      
      // Check for VMware management VMs
      const vmwareManagementIndicators = [
        'vcenter', 'esxi', 'nsx', 'vsan', 'vrops', 'vrealize', 
        'horizon', 'workspace', 'vmware', 'vsphere', 'vcloud'
      ];
      
      const vmwareManagementVMs = vmInventory.filter(vm => {
        const vmName = vm.vm_name?.toLowerCase() || '';
        return vmwareManagementIndicators.some(indicator => vmName.includes(indicator));
      });
      
      // Add VMware management VMs to out of scope items
      vmwareManagementVMs.forEach(vm => {
        outOfScopeItems.push({
          vm_name: vm.vm_name,
          reason: 'VMware management infrastructure component',
          category: 'vmware_management',
          auto_detected: true
        });
      });
      
      // Check for VMware containerization platform VMs
      const containerPlatformIndicators = [
        'tanzu', 'kubernetes', 'k8s', 'container', 'docker', 'harbor', 'registry'
      ];
      
      const containerPlatformVMs = vmInventory.filter(vm => {
        const vmName = vm.vm_name?.toLowerCase() || '';
        return containerPlatformIndicators.some(indicator => vmName.includes(indicator)) &&
               !vmwareManagementVMs.includes(vm); // Avoid duplicates
      });
      
      // Add container platform VMs to out of scope items
      containerPlatformVMs.forEach(vm => {
        outOfScopeItems.push({
          vm_name: vm.vm_name,
          reason: 'VMware containerization platform component',
          category: 'containerization_platform',
          auto_detected: true
        });
      });
      
      // Check for infrastructure VMs (not including legacy OS which are migration blockers)
      const infrastructureIndicators = [
        'infra', 'infrastructure', 'backup', 'monitor', 'proxy', 'gateway', 'firewall'
      ];
      
      const infrastructureVMs = vmInventory.filter(vm => {
        const vmName = vm.vm_name?.toLowerCase() || '';
        return infrastructureIndicators.some(indicator => vmName.includes(indicator)) &&
               !vmwareManagementVMs.includes(vm) && 
               !containerPlatformVMs.includes(vm); // Avoid duplicates
      });
      
      // Add infrastructure VMs to out of scope items
      infrastructureVMs.forEach(vm => {
        outOfScopeItems.push({
          vm_name: vm.vm_name,
          reason: 'Infrastructure component that may require special handling',
          category: 'infrastructure',
          auto_detected: true
        });
      });

      // Create workload classifications based on real data
      const workloadClassifications = [];
      
      if (windowsVMs.length > 0) {
        workloadClassifications.push({
          classification: 'Windows Servers',
          vm_count: windowsVMs.length,
          percentage: Math.round((windowsVMs.length / vmInventory.length) * 100),
          vm_names: windowsVMs.slice(0, 5).map(vm => vm.vm_name) // Show first 5
        });
      }
      
      if (linuxVMs.length > 0) {
        workloadClassifications.push({
          classification: 'Linux Servers',
          vm_count: linuxVMs.length,
          percentage: Math.round((linuxVMs.length / vmInventory.length) * 100),
          vm_names: linuxVMs.slice(0, 5).map(vm => vm.vm_name)
        });
      }
      
      if (otherVMs.length > 0) {
        workloadClassifications.push({
          classification: 'Other/Unknown',
          vm_count: otherVMs.length,
          percentage: Math.round((otherVMs.length / vmInventory.length) * 100),
          vm_names: otherVMs.slice(0, 5).map(vm => vm.vm_name)
        });
      }

      // Calculate in-scope VMs (total VMs minus out of scope VMs)
      const inScopeCount = vmInventory.length - outOfScopeItems.length;
      
      // Add in-scope classification
      workloadClassifications.unshift({
        classification: 'In-Scope Servers',
        vm_count: inScopeCount,
        percentage: Math.round((inScopeCount / vmInventory.length) * 100),
        vm_names: []
      });

      // Filter in-scope VMs
      const inScopeVMs = vmInventory.filter(vm => 
        !outOfScopeItems.some(item => item.vm_name === vm.vm_name)
      );

      // Calculate infrastructure insights based on in-scope VMs only
      const inScopeWindowsVMs = inScopeVMs.filter(vm => 
        vm.os_type?.toLowerCase().includes('windows') || 
        vm.os_type?.toLowerCase().includes('microsoft')
      );
      const inScopeLinuxVMs = inScopeVMs.filter(vm => 
        vm.os_type?.toLowerCase().includes('linux') || 
        vm.os_type?.toLowerCase().includes('ubuntu') || 
        vm.os_type?.toLowerCase().includes('centos') || 
        vm.os_type?.toLowerCase().includes('rhel')
      );
      const inScopeOtherVMs = inScopeVMs.filter(vm => 
        !inScopeWindowsVMs.includes(vm) && !inScopeLinuxVMs.includes(vm)
      );

      const inScopeAvgCpu = inScopeVMs.length > 0 ? 
        inScopeVMs.reduce((sum, vm) => sum + (vm.cpu_count || 2), 0) / inScopeVMs.length : 0;
      const inScopeAvgMemory = inScopeVMs.length > 0 ? 
        inScopeVMs.reduce((sum, vm) => sum + ((vm.memory_mb || 4096) / 1024), 0) / inScopeVMs.length : 0;

      // Create migration scope analysis data with real insights
      const migrationScopeData = {
        session_id: sessionId,
        total_vms: vmInventory.length,
        estimated_timeline_months: Math.max(3, Math.ceil(inScopeVMs.length / 20)), // 20 VMs per month
        complexity_score: Math.round(complexityScore * 10) / 10,
        migration_blockers: migrationBlockers,
        out_of_scope_items: outOfScopeItems,
        workload_classifications: workloadClassifications,
        infrastructure_insights: {
          total_vms: inScopeVMs.length,
          total_storage_tb: inScopeVMs.reduce((sum, vm) => sum + (vm.disk_gb || 100), 0) / 1024,
          os_breakdown: {
            'Windows': inScopeWindowsVMs.length,
            'Linux': inScopeLinuxVMs.length,
            'Other': inScopeOtherVMs.length
          },
          prod_nonprod_ratio: {
            'Production': Math.ceil(inScopeVMs.length * 0.7), // Estimate
            'Non-Production': Math.floor(inScopeVMs.length * 0.3)
          },
          average_vm_specs: {
            'CPU Cores': Math.round(inScopeAvgCpu * 10) / 10,
            'Memory GB': Math.round(inScopeAvgMemory * 10) / 10,
            'Storage GB': inScopeVMs.length > 0 ? 
              Math.round((inScopeVMs.reduce((sum, vm) => sum + (vm.disk_gb || 100), 0) / inScopeVMs.length) * 10) / 10 : 0
          },
          total_resources: {
            'Total CPU Cores': inScopeVMs.reduce((sum, vm) => sum + (vm.cpu_count || 2), 0),
            'Total Memory GB': Math.round(inScopeVMs.reduce((sum, vm) => sum + ((vm.memory_mb || 4096) / 1024), 0)),
            'Total Storage GB': inScopeVMs.reduce((sum, vm) => sum + (vm.disk_gb || 100), 0)
          }
        }
      };
      
      dispatch({ type: 'SET_MIGRATION_SCOPE_ANALYSIS', payload: migrationScopeData });
    } catch (error: any) {
      dispatch({
        type: 'SET_ERROR',
        payload: {
          hasError: true,
          message: error.message || 'Failed to analyze migration scope',
          details: error,
        },
      });
    }
  };
