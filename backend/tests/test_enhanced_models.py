"""
Unit tests for enhanced pricing calculator models
Tests TCOParameters, SavingsPlansPrice, OSSpecificPricing, and regional configuration
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

# Import the models to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.core_models import TCOParameters
from services.aws_pricing_service import (
    SavingsPlansPrice, 
    OSSpecificPricing, 
    EnhancedInstancePricing,
    AWSRegionConfig
)


class TestEnhancedTCOParameters:
    """Test enhanced TCO parameters model"""
    
    def test_valid_enhanced_parameters(self):
        """Test valid enhanced TCO parameters"""
        params = TCOParameters(
            target_region="us-east-1",
            production_pricing_model="compute_savings",
            non_production_pricing_model="on_demand",
            savings_plan_commitment="3_year",
            production_utilization_percent=100,
            non_production_utilization_percent=50,
            default_os_type="linux"
        )
        
        assert params.production_pricing_model == "compute_savings"
        assert params.non_production_pricing_model == "on_demand"
        assert params.savings_plan_commitment == "3_year"
        assert params.production_utilization_percent == 100
        assert params.non_production_utilization_percent == 50
        assert params.default_os_type == "linux"
    
    def test_backward_compatibility(self):
        """Test backward compatibility with legacy parameters"""
        params = TCOParameters(
            target_region="us-east-1",
            pricing_model="mixed",  # Legacy parameter
            production_ri_years=3   # Legacy parameter
        )
        
        assert params.pricing_model == "mixed"
        assert params.production_ri_years == 3
        # Should use defaults for new parameters
        assert params.production_pricing_model == "reserved"
        assert params.non_production_pricing_model == "on_demand"
    
    def test_invalid_utilization_percentage(self):
        """Test validation for invalid utilization percentages"""
        with pytest.raises(ValidationError):
            TCOParameters(production_utilization_percent=120)  # > 100
        
        with pytest.raises(ValidationError):
            TCOParameters(non_production_utilization_percent=20)  # < 25
    
    def test_invalid_pricing_model(self):
        """Test validation for invalid pricing models"""
        with pytest.raises(ValidationError):
            TCOParameters(production_pricing_model="invalid_model")
        
        with pytest.raises(ValidationError):
            TCOParameters(non_production_pricing_model="spot_instances")
    
    def test_invalid_os_type(self):
        """Test validation for invalid OS types"""
        with pytest.raises(ValidationError):
            TCOParameters(default_os_type="invalid_os")
    
    def test_invalid_savings_plan_commitment(self):
        """Test validation for invalid Savings Plans commitment"""
        with pytest.raises(ValidationError):
            TCOParameters(savings_plan_commitment="5_year")
    
    def test_default_values(self):
        """Test default values for enhanced parameters"""
        params = TCOParameters()
        
        assert params.target_region == "us-east-1"
        assert params.production_pricing_model == "reserved"
        assert params.non_production_pricing_model == "on_demand"
        assert params.savings_plan_commitment == "1_year"
        assert params.savings_plan_payment == "no_upfront"
        assert params.production_utilization_percent == 100
        assert params.non_production_utilization_percent == 50
        assert params.default_os_type == "linux"
        assert params.enable_spot_instances == False


class TestSavingsPlansPrice:
    """Test Savings Plans pricing model"""
    
    def test_savings_plans_price_calculation(self):
        """Test Savings Plans price calculations"""
        savings_plan = SavingsPlansPrice(
            plan_type="compute",
            instance_family="m5",
            commitment_term="1_year",
            payment_option="no_upfront",
            hourly_rate=0.05,
            upfront_cost=0.0,
            on_demand_equivalent=0.08
        )
        
        # Should calculate effective hourly rate and savings percentage
        assert savings_plan.effective_hourly_rate == 0.05
        assert savings_plan.savings_percentage == 37.5  # (0.08 - 0.05) / 0.08 * 100
    
    def test_savings_plans_with_upfront_cost(self):
        """Test Savings Plans with upfront costs"""
        savings_plan = SavingsPlansPrice(
            plan_type="ec2_instance",
            instance_family="m5",
            commitment_term="3_year",
            payment_option="all_upfront",
            hourly_rate=0.0,
            upfront_cost=1000.0,
            on_demand_equivalent=0.08
        )
        
        # Should calculate effective hourly rate including upfront amortization
        # 3 years = 26,280 hours, so upfront hourly = 1000 / 26280 ≈ 0.038
        expected_effective_rate = 1000.0 / 26280
        assert abs(savings_plan.effective_hourly_rate - expected_effective_rate) < 0.001
    
    def test_savings_plans_break_even_calculation(self):
        """Test break-even calculation for Savings Plans"""
        savings_plan = SavingsPlansPrice(
            plan_type="compute",
            instance_family="m5",
            commitment_term="1_year",
            payment_option="partial_upfront",
            hourly_rate=0.03,
            upfront_cost=200.0,
            on_demand_equivalent=0.08
        )
        
        # Effective rate should include upfront amortization
        upfront_hourly = 200.0 / 8760  # 1 year = 8760 hours
        expected_effective_rate = 0.03 + upfront_hourly
        assert abs(savings_plan.effective_hourly_rate - expected_effective_rate) < 0.001


class TestOSSpecificPricing:
    """Test OS-specific pricing model"""
    
    def test_linux_pricing(self):
        """Test Linux pricing (no additional costs)"""
        linux_pricing = OSSpecificPricing(
            os_type="linux",
            base_hourly_rate=0.08,
            license_cost_hourly=0.0,
            support_cost_hourly=0.0
        )
        
        assert linux_pricing.total_hourly_rate == 0.08
    
    def test_windows_pricing(self):
        """Test Windows pricing with licensing costs"""
        windows_pricing = OSSpecificPricing(
            os_type="windows",
            base_hourly_rate=0.08,
            license_cost_hourly=0.048,  # Windows Server licensing
            support_cost_hourly=0.0
        )
        
        assert windows_pricing.total_hourly_rate == 0.128  # 0.08 + 0.048
    
    def test_rhel_pricing(self):
        """Test RHEL pricing with licensing and support costs"""
        rhel_pricing = OSSpecificPricing(
            os_type="rhel",
            base_hourly_rate=0.08,
            license_cost_hourly=0.09,   # Red Hat licensing
            support_cost_hourly=0.01   # Red Hat support
        )
        
        assert rhel_pricing.total_hourly_rate == 0.18  # 0.08 + 0.09 + 0.01


class TestEnhancedInstancePricing:
    """Test enhanced instance pricing model"""
    
    def test_get_os_pricing(self):
        """Test OS-specific pricing retrieval"""
        linux_pricing = OSSpecificPricing("linux", 0.08)
        windows_pricing = OSSpecificPricing("windows", 0.08, 0.048)
        
        enhanced_pricing = EnhancedInstancePricing(
            instance_type="m5.large",
            region="us-east-1",
            instance_family="m5",
            linux_pricing=linux_pricing,
            windows_pricing=windows_pricing
        )
        
        assert enhanced_pricing.get_os_pricing("linux") == linux_pricing
        assert enhanced_pricing.get_os_pricing("windows") == windows_pricing
        assert enhanced_pricing.get_os_pricing("rhel") is None
    
    def test_get_best_savings_plan(self):
        """Test best Savings Plans selection"""
        compute_savings = SavingsPlansPrice(
            plan_type="compute",
            instance_family="m5",
            commitment_term="1_year",
            payment_option="no_upfront",
            hourly_rate=0.06,
            on_demand_equivalent=0.08
        )
        
        ec2_savings = SavingsPlansPrice(
            plan_type="ec2_instance",
            instance_family="m5",
            commitment_term="1_year",
            payment_option="no_upfront",
            hourly_rate=0.05,
            on_demand_equivalent=0.08
        )
        
        enhanced_pricing = EnhancedInstancePricing(
            instance_type="m5.large",
            region="us-east-1",
            instance_family="m5",
            linux_pricing=OSSpecificPricing("linux", 0.08),
            compute_savings_plans={"1_year_no_upfront": compute_savings},
            ec2_savings_plans={"1_year_no_upfront": ec2_savings}
        )
        
        # Should prefer EC2 Instance Savings Plans (better savings)
        best_plan = enhanced_pricing.get_best_savings_plan("1_year", "no_upfront")
        assert best_plan == ec2_savings
        assert best_plan.hourly_rate == 0.05


class TestAWSRegionConfig:
    """Test AWS region configuration"""
    
    def test_get_region_info(self):
        """Test region information retrieval"""
        region_info = AWSRegionConfig.get_region_info('us-east-1')
        
        assert region_info['name'] == 'US East (N. Virginia)'
        assert region_info['pricing_tier'] == 'standard'
        assert region_info['supports_savings_plans'] == True
        assert region_info['availability_zones'] == 6
    
    def test_supports_savings_plans(self):
        """Test Savings Plans support check"""
        assert AWSRegionConfig.supports_savings_plans('us-east-1') == True
        assert AWSRegionConfig.supports_savings_plans('af-south-1') == False
        assert AWSRegionConfig.supports_savings_plans('invalid-region') == False
    
    def test_get_pricing_tier(self):
        """Test pricing tier retrieval"""
        assert AWSRegionConfig.get_pricing_tier('us-east-1') == 'standard'
        assert AWSRegionConfig.get_pricing_tier('us-west-1') == 'premium'
        assert AWSRegionConfig.get_pricing_tier('invalid-region') == 'standard'
    
    def test_get_all_regions(self):
        """Test all regions retrieval"""
        all_regions = AWSRegionConfig.get_all_regions()
        
        assert len(all_regions) >= 25  # Should have 25+ regions
        assert all(isinstance(region, dict) for region in all_regions)
        assert all('code' in region and 'name' in region for region in all_regions)
        
        # Check specific regions exist
        region_codes = [region['code'] for region in all_regions]
        assert 'us-east-1' in region_codes
        assert 'eu-west-1' in region_codes
        assert 'ap-southeast-1' in region_codes
    
    def test_get_location_name(self):
        """Test AWS Pricing API location name retrieval"""
        assert AWSRegionConfig.get_location_name('us-east-1') == 'US East (N. Virginia)'
        assert AWSRegionConfig.get_location_name('eu-west-1') == 'Europe (Ireland)'
        assert AWSRegionConfig.get_location_name('invalid-region') == 'invalid-region'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
