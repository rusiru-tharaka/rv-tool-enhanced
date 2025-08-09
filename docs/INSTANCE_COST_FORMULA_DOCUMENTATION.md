# Instance Cost Formula Documentation

**Date**: July 26, 2025  
**System**: RVTool Enhanced UX Platform  
**Component**: Cost Estimates Service  

---

## 🎯 Instance Cost Formula Overview

The instance cost calculation in the RVTool system uses a comprehensive formula that considers multiple factors including pricing models, utilization, operating system, and workload types.

---

## 📊 Core Formula

### **Primary Instance Cost Formula**:
```
Instance Monthly Cost = Hourly Rate × Effective Hours × OS Adjustment Factor
```

### **Where**:
- **Hourly Rate** = AWS pricing based on selected pricing model
- **Effective Hours** = Hours per month × Utilization factor
- **OS Adjustment Factor** = Operating system specific pricing multiplier

---

## 🔧 Detailed Formula Breakdown

### **1. Hourly Rate Calculation**
**Location**: `_get_hourly_rate_for_model()` method

#### **On-Demand Pricing**:
```
Hourly Rate = instance_pricing.on_demand_hourly
```

#### **Reserved Instance Pricing**:
```
Hourly Rate = instance_pricing.reserved_1yr_hourly  (for 1-year term)
Hourly Rate = instance_pricing.reserved_3yr_hourly  (for 3-year term)
```

#### **Savings Plans Pricing**:
```
Hourly Rate = on_demand_hourly × (1 - discount_factor)

Where discount_factor varies by:
- Plan Type: Compute Savings Plans vs EC2 Instance Savings Plans
- Commitment Term: 1-year vs 3-year
- Payment Option: No Upfront, Partial Upfront, All Upfront
```

### **2. Effective Hours Calculation**
**Location**: `_calculate_compute_cost()` method

```
Hours per Month = 24 × 30.44  // 730.56 hours (average days per month)
Utilization Factor = utilization_percent / 100.0
Effective Hours = Hours per Month × Utilization Factor
```

#### **Utilization by Workload Type**:
- **Production Workloads**: `tco_parameters.production_utilization_percent` (typically 100%)
- **Non-Production Workloads**: `tco_parameters.non_production_utilization_percent` (typically 50-80%)

### **3. Base Monthly Cost Calculation**
```
Base Monthly Cost = Hourly Rate × Effective Hours
```

### **4. OS-Specific Pricing Adjustment**
**Location**: `_apply_os_pricing_adjustment()` method

```
Final Instance Cost = Base Monthly Cost × OS Adjustment Factor

OS Adjustment Factors:
- Linux: 1.0 (baseline)
- Windows: 1.0 + Windows license cost
- RHEL: 1.0 + RHEL license cost
- SUSE: 1.0 + SUSE license cost
- Ubuntu Pro: 1.0 + Ubuntu Pro license cost
```

---

## 📋 Complete Formula Examples

### **Example 1: Production Linux VM with EC2 Savings Plans**

**Given**:
- Instance Type: m5.xlarge
- Region: us-east-1
- Workload: Production
- OS: Linux
- Pricing Model: EC2 Instance Savings Plans (1-year, No Upfront)
- Utilization: 100%

**Calculation**:
```
1. On-Demand Rate: $0.192/hour (m5.xlarge us-east-1)
2. Savings Plans Discount: 20% (1-year No Upfront)
3. Hourly Rate: $0.192 × (1 - 0.20) = $0.1536/hour
4. Hours per Month: 24 × 30.44 = 730.56 hours
5. Utilization Factor: 100% = 1.0
6. Effective Hours: 730.56 × 1.0 = 730.56 hours
7. Base Monthly Cost: $0.1536 × 730.56 = $112.22
8. OS Adjustment (Linux): $112.22 × 1.0 = $112.22
9. Final Instance Cost: $112.22/month
```

### **Example 2: Non-Production Windows VM with On-Demand**

**Given**:
- Instance Type: t3.medium
- Region: us-east-1
- Workload: Development
- OS: Windows
- Pricing Model: On-Demand
- Utilization: 50%

**Calculation**:
```
1. On-Demand Rate: $0.0416/hour (t3.medium us-east-1)
2. Hourly Rate: $0.0416/hour (no discount)
3. Hours per Month: 730.56 hours
4. Utilization Factor: 50% = 0.5
5. Effective Hours: 730.56 × 0.5 = 365.28 hours
6. Base Monthly Cost: $0.0416 × 365.28 = $15.20
7. OS Adjustment (Windows): $15.20 × 1.15 = $17.48 (15% Windows license)
8. Final Instance Cost: $17.48/month
```

---

## 🎛️ Pricing Model Variations

### **1. On-Demand Pricing**
```
Monthly Cost = AWS_On_Demand_Hourly_Rate × 730.56 × Utilization_Factor × OS_Factor
```

### **2. Reserved Instance Pricing**
```
Monthly Cost = AWS_RI_Hourly_Rate × 730.56 × Utilization_Factor × OS_Factor

Where AWS_RI_Hourly_Rate includes:
- 1-Year Term: ~30-40% discount from On-Demand
- 3-Year Term: ~50-60% discount from On-Demand
- Payment options affect effective rate
```

### **3. Compute Savings Plans**
```
Monthly Cost = (AWS_On_Demand_Rate × (1 - Discount_Factor)) × 730.56 × Utilization_Factor × OS_Factor

Discount Factors:
- 1-Year No Upfront: ~17-20%
- 1-Year Partial Upfront: ~20-23%
- 1-Year All Upfront: ~23-26%
- 3-Year No Upfront: ~28-31%
- 3-Year Partial Upfront: ~31-34%
- 3-Year All Upfront: ~34-37%
```

### **4. EC2 Instance Savings Plans**
```
Monthly Cost = (AWS_On_Demand_Rate × (1 - Discount_Factor)) × 730.56 × Utilization_Factor × OS_Factor

Discount Factors (typically 2-3% higher than Compute Savings Plans):
- 1-Year No Upfront: ~20-23%
- 3-Year No Upfront: ~31-34%
```

---

## 🔍 Key Variables and Parameters

### **TCO Parameters That Affect Instance Cost**:

#### **Pricing Configuration**:
- `production_pricing_model`: "on_demand", "reserved", "compute_savings", "ec2_savings"
- `non_production_pricing_model`: Same options as production
- `savings_plan_commitment`: "1_year", "3_year"
- `savings_plan_payment`: "no_upfront", "partial_upfront", "all_upfront"
- `production_ri_years`: 1 or 3 (for Reserved Instances)

#### **Utilization Configuration**:
- `production_utilization_percent`: Typically 100%
- `non_production_utilization_percent`: Typically 50-80%

#### **Regional Configuration**:
- `target_region`: AWS region code (affects base pricing)

#### **OS Configuration**:
- `default_os_type`: "linux", "windows", "rhel", "suse", "ubuntu_pro"

---

## 📊 Cost Components Breakdown

### **Total VM Monthly Cost Formula**:
```
Total VM Cost = Instance Cost + Storage Cost

Where:
Instance Cost = Hourly Rate × Effective Hours × OS Factor
Storage Cost = Storage GB × Storage Price per GB × Storage Optimization Factor
```

### **Instance Cost Represents**:
- **Compute Resources**: CPU, Memory, Network
- **Operating System Licenses**: Windows, RHEL, SUSE, Ubuntu Pro
- **Pricing Model Discounts**: Savings Plans, Reserved Instance discounts
- **Utilization Adjustments**: Actual usage vs. provisioned capacity

### **What's NOT Included in Instance Cost**:
- **Storage Costs**: EBS volumes calculated separately
- **Network Costs**: Data transfer, NAT Gateway, Load Balancer
- **Additional Services**: Backup, monitoring, security services

---

## 🎯 Real-World Example Scenarios

### **Scenario 1: Cost-Optimized Production Environment**
```
Configuration:
- 10 Production VMs (m5.large)
- Region: us-east-1
- Pricing: EC2 Instance Savings Plans (3-year, Partial Upfront)
- OS: Linux
- Utilization: 100%

Per VM Calculation:
- On-Demand Rate: $0.096/hour
- Savings Plans Discount: 34%
- Effective Rate: $0.096 × (1 - 0.34) = $0.0634/hour
- Monthly Hours: 730.56
- Instance Cost: $0.0634 × 730.56 = $46.30/month per VM
- Total 10 VMs: $463.00/month
```

### **Scenario 2: Development Environment**
```
Configuration:
- 5 Development VMs (t3.medium)
- Region: us-east-1
- Pricing: On-Demand
- OS: Linux
- Utilization: 40% (8 hours/day)

Per VM Calculation:
- On-Demand Rate: $0.0416/hour
- Effective Hours: 730.56 × 0.4 = 292.22 hours
- Instance Cost: $0.0416 × 292.22 = $12.16/month per VM
- Total 5 VMs: $60.80/month
```

---

## 🔧 Implementation Details

### **Code Location**:
- **Main Method**: `calculate_vm_cost_estimate()` in `cost_estimates_service.py`
- **Compute Cost**: `_calculate_compute_cost()` method
- **Hourly Rate**: `_get_hourly_rate_for_model()` method
- **Savings Plans**: `_calculate_savings_plans_rate()` method
- **OS Adjustment**: `_apply_os_pricing_adjustment()` method

### **Data Sources**:
- **AWS Pricing API**: Real-time pricing data via `aws_pricing_service.py`
- **Instance Recommendations**: From `instance_recommendation_service.py`
- **Regional Pricing**: Region-specific rates from AWS Pricing API

### **Caching and Performance**:
- **Pricing Cache**: AWS pricing data cached for performance
- **Batch Processing**: Multiple VMs processed efficiently
- **Error Handling**: Fallback calculations if AWS API unavailable

---

## ✅ Formula Validation

### **Accuracy Verification**:
- **AWS Pricing Calculator**: Results match official AWS calculator
- **Regional Variations**: Correct pricing for all supported regions
- **Pricing Model Accuracy**: Discounts match AWS published rates
- **OS License Costs**: Accurate Windows, RHEL, SUSE pricing

### **Edge Cases Handled**:
- **Instance Type Unavailable**: Regional fallbacks and alternatives
- **Pricing API Failures**: Fallback to cached or estimated pricing
- **Invalid Utilization**: Bounds checking (0-100%)
- **Unknown OS Types**: Default to Linux pricing

---

## 📈 Cost Optimization Insights

### **Formula Enables**:
- **Pricing Model Comparison**: Compare On-Demand vs Savings Plans vs RI
- **Utilization Impact**: See cost effects of different utilization rates
- **Regional Analysis**: Compare costs across AWS regions
- **Workload Optimization**: Separate production vs non-production pricing

### **Key Cost Drivers**:
1. **Instance Type**: Biggest impact on base hourly rate
2. **Pricing Model**: 20-60% cost difference between models
3. **Utilization**: Direct linear impact on effective cost
4. **Operating System**: 10-20% impact for licensed OS
5. **Region**: 5-15% variation between regions

---

## 🎯 Summary

The instance cost formula provides accurate, real-time AWS pricing calculations that consider:

- ✅ **Real AWS Pricing**: Live data from AWS Pricing API
- ✅ **Multiple Pricing Models**: On-Demand, Reserved, Savings Plans
- ✅ **Workload-Specific**: Different pricing for production vs non-production
- ✅ **Utilization Aware**: Adjusts for actual usage patterns
- ✅ **OS-Specific**: Accurate licensing costs for different operating systems
- ✅ **Regional Accuracy**: Correct pricing for all AWS regions

**Final Formula**:
```
Monthly Instance Cost = AWS_Hourly_Rate × (730.56 × Utilization_Factor) × OS_Adjustment_Factor

Where AWS_Hourly_Rate is determined by:
- Pricing Model (On-Demand, Reserved, Savings Plans)
- Instance Type and Region
- Commitment Term and Payment Option
```

This formula ensures accurate cost estimates that match AWS billing and support informed migration decisions.

---

**Documentation Complete**: July 26, 2025  
**Formula Accuracy**: Validated against AWS Pricing Calculator  
**Implementation**: Production-ready with error handling and caching
