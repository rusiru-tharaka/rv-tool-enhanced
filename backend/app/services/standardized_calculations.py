
def calculate_standardized_instance_cost(vm_spec, tco_params):
    """
    Standardized instance cost calculation ensuring consistency
    """
    # Get base pricing
    instance_type = vm_spec.get('recommended_instance_type')
    region = tco_params.get('target_region', 'ap-southeast-1')
    environment = vm_spec.get('environment', 'Non-Production')
    
    # Determine pricing model
    if environment == 'Production':
        pricing_model = tco_params.get('production_model', 'reserved_instance')
        if pricing_model == 'reserved_instance':
            term = tco_params.get('savings_plan_term', '3_year')
            payment = tco_params.get('savings_plan_payment', 'no_upfront')
            pricing_key = f'reserved_{term}_{payment}'
        else:
            pricing_key = 'on_demand'
    else:
        pricing_key = 'on_demand'
    
    # Get hourly rate
    hourly_rate = get_instance_hourly_rate(instance_type, region, pricing_key)
    
    # Apply utilization factor
    if environment == 'Non-Production':
        utilization = 0.5  # 50% utilization
    else:
        utilization = 1.0  # 100% utilization
    
    # Calculate monthly cost
    hours_per_month = 24 * 30.44  # Average month
    monthly_cost = hourly_rate * hours_per_month * utilization
    
    return {
        'hourly_rate': hourly_rate,
        'utilization': utilization,
        'monthly_cost': monthly_cost,
        'pricing_model': pricing_key
    }

def get_instance_hourly_rate(instance_type, region, pricing_model):
    """Get hourly rate for specific instance type and pricing model"""
    # Load Singapore pricing data
    with open('/home/ubuntu/rvtool/enhanced-ux/backend/data/singapore_pricing.json', 'r') as f:
        pricing_data = json.load(f)
    
    if region == 'ap-southeast-1' and instance_type in pricing_data['instance_pricing']:
        return pricing_data['instance_pricing'][instance_type].get(pricing_model, 0)
    
    # Fallback to AWS API or default pricing
    return 0
