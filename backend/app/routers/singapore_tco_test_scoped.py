"""
Singapore TCO Test Router - Scoped Version
Uses existing application methodology for data extraction and recommendations
MODIFIED: Only calculates TCO for in-scope servers from Migration Analysis Phase
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..services.session_manager import session_manager
from ..services.cost_estimates_service import cost_estimates_service
from ..services.migration_scope_service import migration_scope_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/singapore-tco-test", tags=["Singapore TCO Test - Scoped"])

# Hardcoded Singapore pricing data (ap-southeast-1) - Only for pricing override
SINGAPORE_PRICING = {
    'instance_pricing': {
        't3.micro': {
            'on_demand': 0.0128,
            'reserved_3y_no_upfront': 0.0077
        },
        't3.small': {
            'on_demand': 0.0256,
            'reserved_3y_no_upfront': 0.0154
        },
        't3.medium': {
            'on_demand': 0.0512,
            'reserved_3y_no_upfront': 0.0308
        },
        't3.large': {
            'on_demand': 0.1024,
            'reserved_3y_no_upfront': 0.0616
        },
        't3.xlarge': {
            'on_demand': 0.2048,
            'reserved_3y_no_upfront': 0.1232
        },
        't3.2xlarge': {
            'on_demand': 0.4096,
            'reserved_3y_no_upfront': 0.2464
        },
        'm5.large': {
            'on_demand': 0.116,
            'reserved_3y_no_upfront': 0.070
        },
        'm5.xlarge': {
            'on_demand': 0.232,
            'reserved_3y_no_upfront': 0.140
        },
        'm5.2xlarge': {
            'on_demand': 0.464,
            'reserved_3y_no_upfront': 0.280
        },
        'm5.4xlarge': {
            'on_demand': 0.928,
            'reserved_3y_no_upfront': 0.560
        },
        'm5.8xlarge': {
            'on_demand': 1.856,
            'reserved_3y_no_upfront': 1.120
        },
        'm5.12xlarge': {
            'on_demand': 2.784,
            'reserved_3y_no_upfront': 1.680
        }
    },
    'storage_pricing': {
        'gp3': 0.092  # per GB per month
    }
}

async def filter_in_scope_vms(session_id: str, vm_inventory: List[Dict]) -> tuple[List[Dict], List[str], Dict]:
    """
    Filter VM inventory to include only in-scope VMs based on Migration Analysis
    UPDATED: Now uses stored Migration Scope analysis results for consistency
    
    Args:
        session_id: Session identifier
        vm_inventory: Full VM inventory from session
        
    Returns:
        Tuple of (in_scope_vms, out_of_scope_vm_names, scope_info)
    """
    try:
        logger.info(f"Getting migration scope analysis for session {session_id}")
        
        # STEP 1: Try to get stored Migration Scope analysis results first
        stored_analysis = session_manager.get_migration_scope_analysis(session_id)
        
        if stored_analysis:
            logger.info("✅ Using stored Migration Scope analysis results (consistent with frontend)")
            logger.info(f"Stored analysis contains {len(stored_analysis.get('out_of_scope_items', []))} out-of-scope items")
            
            # Use stored results for consistent filtering
            out_of_scope_items = stored_analysis.get('out_of_scope_items', [])
            out_of_scope_vm_names = [item.get('vm_name') for item in out_of_scope_items if item.get('vm_name')]
            
            logger.info(f"Out-of-scope VMs from stored analysis: {out_of_scope_vm_names}")
            
        else:
            logger.warning("⚠️ No stored Migration Scope analysis found, falling back to fresh analysis")
            
            # STEP 2: Fallback - run fresh Migration Scope analysis
            migration_analysis = await migration_scope_service.analyze_migration_scope(
                session_id, vm_inventory
            )
            
            # Extract out-of-scope VM names from fresh analysis
            out_of_scope_vm_names = [item.vm_name for item in migration_analysis.out_of_scope_items]
            out_of_scope_items = [
                {
                    'vm_name': item.vm_name,
                    'reason': item.reason,
                    'category': item.category
                }
                for item in migration_analysis.out_of_scope_items
            ]
            
            logger.info(f"Out-of-scope VMs from fresh analysis: {out_of_scope_vm_names}")
        
        # STEP 3: Filter VM inventory to exclude out-of-scope VMs
        in_scope_vms = []
        for vm in vm_inventory:
            vm_name = vm.get('vm_name', vm.get('VM', 'Unknown'))
            if vm_name not in out_of_scope_vm_names:
                in_scope_vms.append(vm)
            else:
                logger.info(f"🚫 Filtering out VM: {vm_name} (out-of-scope)")
        
        # STEP 4: Create scope information for response
        scope_info = {
            'total_vms': len(vm_inventory),
            'in_scope_vms': len(in_scope_vms),
            'out_of_scope_vms': len(out_of_scope_vm_names),
            'out_of_scope_details': out_of_scope_items if 'out_of_scope_items' in locals() else [
                {'vm_name': name, 'reason': 'From stored analysis', 'category': 'stored'}
                for name in out_of_scope_vm_names
            ],
            'filtering_applied': True,
            'analysis_source': 'stored' if stored_analysis else 'fresh'
        }
        
        logger.info(f"✅ Filtering complete: {len(vm_inventory)} total → {len(in_scope_vms)} in-scope")
        logger.info(f"📊 Scope summary: {scope_info}")
        
        return in_scope_vms, out_of_scope_vm_names, scope_info
        
    except Exception as e:
        logger.error(f"❌ Failed to get migration scope analysis: {e}")
        logger.info("🔄 Proceeding with all VMs (no filtering applied)")
        
        # Fallback: return all VMs if both stored and fresh analysis fail
        scope_info = {
            'total_vms': len(vm_inventory),
            'in_scope_vms': len(vm_inventory),
            'out_of_scope_vms': 0,
            'out_of_scope_details': [],
            'filtering_applied': False,
            'fallback_reason': f"Migration scope analysis failed: {str(e)}"
        }
        
        return vm_inventory, [], scope_info

def apply_singapore_pricing_to_vm(vm_name: str, cpu_cores: int, memory_gb: float, storage_gb: float, instance_type: str, environment: str) -> Dict:
    """Apply Singapore pricing directly to VM data"""
    try:
        # Determine pricing model based on environment (hardcoded as requested)
        if environment == 'Production':
            pricing_key = 'reserved_3y_no_upfront'
            pricing_plan = 'Reserved Instance (3 Year)'
            utilization = 1.0
        else:
            pricing_key = 'on_demand'
            pricing_plan = 'On-Demand'
            utilization = 0.5  # 50% utilization for non-production
        
        # Get Singapore hourly rate
        if instance_type in SINGAPORE_PRICING['instance_pricing']:
            hourly_rate = SINGAPORE_PRICING['instance_pricing'][instance_type][pricing_key]
        else:
            logger.warning(f"No Singapore pricing for {instance_type}, using m5.xlarge as fallback")
            hourly_rate = SINGAPORE_PRICING['instance_pricing']['m5.xlarge'][pricing_key]
        
        # Calculate costs with Singapore pricing
        hours_per_month = 24 * 30.44
        instance_monthly_cost = hourly_rate * hours_per_month * utilization
        storage_monthly_cost = storage_gb * SINGAPORE_PRICING['storage_pricing']['gp3']
        total_monthly_cost = instance_monthly_cost + storage_monthly_cost
        
        return {
            'vmName': vm_name,
            'cpuCores': cpu_cores,
            'memoryGB': round(memory_gb, 1),
            'storageGB': round(storage_gb, 2),
            'recommendedInstanceType': instance_type,
            'instanceCost': round(instance_monthly_cost, 2),
            'storageCost': round(storage_monthly_cost, 2),
            'totalMonthlyCost': round(total_monthly_cost, 2),
            'pricingPlan': pricing_plan,
            'operatingSystem': 'Linux',  # Default for now
            'environment': environment,
            'hourlyRate': hourly_rate,
            'utilization': utilization
        }
        
    except Exception as e:
        logger.error(f"Error applying Singapore pricing to {vm_name}: {e}")
        return None

@router.post("/{session_id}")
async def calculate_singapore_tco_test_scoped(session_id: str, tco_parameters: Dict[str, Any]):
    """
    Calculate Singapore TCO test for IN-SCOPE VMs ONLY
    
    Args:
        session_id: Session identifier
        tco_parameters: TCO parameters (will be overridden with hardcoded Singapore values)
    
    Returns:
        VM cost analysis with Singapore pricing for in-scope VMs only
    """
    try:
        logger.info(f"🚀 [Singapore TCO Backend] Starting SCOPED Singapore TCO test for session {session_id}")
        
        # Get session and VM inventory using existing session manager
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        vm_inventory = session.vm_inventory
        if not vm_inventory:
            raise HTTPException(status_code=404, detail=f"Session {session_id} has no VM data")
        
        logger.info(f"📊 [Singapore TCO Backend] Found {len(vm_inventory)} total VMs in session")
        logger.info(f"📋 [Singapore TCO Backend] VM names: {[vm.get('vm_name', vm.get('VM', 'Unknown')) for vm in vm_inventory]}")
        
        # Check if Migration Scope analysis is available
        has_stored_analysis = session_manager.has_migration_scope_analysis(session_id)
        logger.info(f"🔍 [Singapore TCO Backend] Migration Scope analysis available: {has_stored_analysis}")
        
        # FILTER FOR IN-SCOPE VMs ONLY
        logger.info(f"🔄 [Singapore TCO Backend] Starting VM filtering process...")
        in_scope_vms, out_of_scope_vm_names, scope_info = await filter_in_scope_vms(session_id, vm_inventory)
        
        logger.info(f"📊 [Singapore TCO Backend] Filtering results:")
        logger.info(f"   Total VMs: {scope_info.get('total_vms', 0)}")
        logger.info(f"   In-scope VMs: {scope_info.get('in_scope_vms', 0)}")
        logger.info(f"   Out-of-scope VMs: {scope_info.get('out_of_scope_vms', 0)}")
        logger.info(f"   Analysis source: {scope_info.get('analysis_source', 'unknown')}")
        
        if out_of_scope_vm_names:
            logger.info(f"❌ [Singapore TCO Backend] Out-of-scope VMs: {out_of_scope_vm_names}")
        else:
            logger.info(f"✅ [Singapore TCO Backend] No out-of-scope VMs found")
        
        if not in_scope_vms:
            logger.warning(f"⚠️ [Singapore TCO Backend] No in-scope VMs found for session {session_id}")
            return JSONResponse(content={
                'session_id': session_id,
                'error': 'No in-scope VMs found for analysis',
                'scope_info': scope_info,
                'vm_costs': [],
                'summary': {
                    'total_vms': 0,
                    'total_monthly_cost': 0.0,
                    'total_annual_cost': 0.0,
                    'average_monthly_cost_per_vm': 0.0
                }
            })
        
        logger.info(f"💰 [Singapore TCO Backend] Processing {len(in_scope_vms)} in-scope VMs (filtered from {len(vm_inventory)} total)")
        logger.info(f"💰 [Singapore TCO Backend] In-scope VM names: {[vm.get('vm_name', vm.get('VM', 'Unknown')) for vm in in_scope_vms]}")
        
        # Process IN-SCOPE VMs only
        vm_costs = []
        
        for vm_data in in_scope_vms:
            try:
                # Extract VM data directly from the inventory structure
                vm_name = vm_data.get('vm_name', vm_data.get('VM', 'Unknown'))
                cpu_cores = int(vm_data.get('cpu_count', vm_data.get('CPUs', 1)))
                memory_mb = float(vm_data.get('memory_mb', vm_data.get('Memory', 1024)))
                storage_gb = float(vm_data.get('disk_gb', vm_data.get('storage_gb', 0)))
                
                # Convert memory from MB to GB
                memory_gb = memory_mb / 1024
                
                # Get instance recommendation using existing service
                from ..services.instance_recommendation_service import recommendation_service, VMSpecification, WorkloadType
                
                # Create VM specification for recommendation
                vm_spec = VMSpecification(
                    vm_name=vm_name,
                    cpu_cores=cpu_cores,
                    memory_gb=memory_gb,
                    storage_gb=storage_gb,
                    workload_type=WorkloadType.PRODUCTION if 'prod' in vm_name.lower() else WorkloadType.DEVELOPMENT,
                    os_type='windows' if 'windows' in vm_data.get('os_type', vm_data.get('OS', '')).lower() else 'linux'
                )
                
                recommendation = recommendation_service.recommend_instance(vm_spec)
                instance_type = recommendation.instance_type
                
                # Determine environment from VM name
                vm_name_lower = vm_name.lower()
                if any(indicator in vm_name_lower for indicator in ['prod', 'dr', 'backup', 'archive']):
                    environment = 'Production'
                elif any(indicator in vm_name_lower for indicator in ['dev', 'test', 'uat', 'demo', 'staging']):
                    environment = 'Non-Production'
                else:
                    # Default based on size
                    environment = 'Production' if (cpu_cores >= 4 or memory_gb >= 16) else 'Non-Production'
                
                # Apply Singapore pricing
                vm_cost = apply_singapore_pricing_to_vm(
                    vm_name, cpu_cores, memory_gb, storage_gb, instance_type, environment
                )
                
                if vm_cost:
                    vm_costs.append(vm_cost)
                    
            except Exception as e:
                logger.error(f"Error processing VM {vm_data.get('vm_name', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Successfully processed {len(vm_costs)} in-scope VMs")
        
        # Calculate summary statistics
        total_monthly_cost = sum(vm['totalMonthlyCost'] for vm in vm_costs)
        total_annual_cost = total_monthly_cost * 12
        
        result = {
            'session_id': session_id,
            'tco_parameters': {
                'target_region': 'ap-southeast-1',
                'production_model': 'reserved_instance',
                'reserved_instance_term': '3_year',
                'reserved_instance_payment': 'no_upfront',
                'non_production_model': 'on_demand',
                'non_production_utilization': 0.5
            },
            'scope_info': scope_info,  # NEW: Information about filtering
            'vm_costs': vm_costs,
            'summary': {
                'total_vms': len(vm_costs),
                'total_monthly_cost': round(total_monthly_cost, 2),
                'total_annual_cost': round(total_annual_cost, 2),
                'average_monthly_cost_per_vm': round(total_monthly_cost / len(vm_costs), 2) if vm_costs else 0
            },
            'methodology': 'existing_application_services_with_scope_filtering',
            'calculation_timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"SCOPED Singapore TCO test completed for session {session_id}: {len(vm_costs)} in-scope VMs, ${total_monthly_cost:.2f}/month")
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SCOPED Singapore TCO test failed for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Singapore TCO test failed: {str(e)}")

@router.get("/pricing-data")
async def get_singapore_pricing_data():
    """Get the hardcoded Singapore pricing data for reference"""
    return JSONResponse(content={
        'region': 'ap-southeast-1',
        'pricing_data': SINGAPORE_PRICING,
        'last_updated': '2025-07-30',
        'source': 'aws_pricing_calculator'
    })
