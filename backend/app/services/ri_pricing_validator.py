
def validate_reserved_instance_pricing():
    """
    Validate Reserved Instance pricing calculations
    """
    # Expected costs for Singapore region (3-year, No Upfront)
    expected_costs = {
        'm5.2xlarge': {
            'hourly_rate': 0.280,
            'monthly_cost': 0.280 * 24 * 30.44,  # $204.29
            'annual_cost': 0.280 * 24 * 365       # $2451.52
        },
        'm5.xlarge': {
            'hourly_rate': 0.140,
            'monthly_cost': 0.140 * 24 * 30.44,  # $102.15
            'annual_cost': 0.140 * 24 * 365       # $1225.76
        }
    }
    
    validation_results = []
    
    for instance_type, expected in expected_costs.items():
        # Calculate actual costs
        actual_hourly = get_instance_hourly_rate(instance_type, 'ap-southeast-1', 'reserved_3y_no_upfront')
        actual_monthly = actual_hourly * 24 * 30.44
        actual_annual = actual_hourly * 24 * 365
        
        # Validate
        hourly_diff = abs(actual_hourly - expected['hourly_rate'])
        monthly_diff = abs(actual_monthly - expected['monthly_cost'])
        annual_diff = abs(actual_annual - expected['annual_cost'])
        
        validation_results.append({
            'instance_type': instance_type,
            'expected_hourly': expected['hourly_rate'],
            'actual_hourly': actual_hourly,
            'hourly_difference': hourly_diff,
            'expected_monthly': expected['monthly_cost'],
            'actual_monthly': actual_monthly,
            'monthly_difference': monthly_diff,
            'validation_passed': hourly_diff < 0.001 and monthly_diff < 1.0
        })
    
    return validation_results
