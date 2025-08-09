# Cost Calculation Inconsistencies Analysis

**Date**: July 30, 2025  
**Issue**: Inconsistent pricing for same instance types in same environment  
**Data Source**: vm-cost-estimates-81bd54c1-8745-4996-a528-a67899a0057e.csv  

---

## 🚨 **IDENTIFIED INCONSISTENCIES**

### **Issue 1: Non-Production m5.2xlarge Pricing Discrepancy**

| VM Name | Instance Type | Environment | Instance Cost | Expected | Discrepancy |
|---------|---------------|-------------|---------------|----------|-------------|
| apache95-demo | m5.2xlarge | Non-Production | $143.47 | Same as router-dev-go | ✅ Consistent |
| router-dev-go | m5.2xlarge | Non-Production | $149.07 | Same as apache95-demo | ❌ **$5.60 difference** |

**Question**: Why do two Non-Production m5.2xlarge instances have different costs?

### **Issue 2: Production m5.xlarge Pricing Discrepancy**

| VM Name | Instance Type | Environment | Instance Cost | Expected | Discrepancy |
|---------|---------------|-------------|---------------|----------|-------------|
| cms92-dr | m5.xlarge | Production | $53.86 | Same as grafana-archive-dr51 | ❌ **$16.53 difference** |
| grafana-archive-dr51 | m5.xlarge | Production | $37.33 | Same as cms92-dr | ❌ **$16.53 difference** |

**Question**: Why do two Production m5.xlarge instances have different costs?

---

## 🔍 **ROOT CAUSE INVESTIGATION**

### **Hypothesis 1: Utilization Factor Differences**
**Theory**: Different utilization percentages applied

**Analysis**:
- **Non-Production**: Should use 50% utilization consistently
- **Production**: Should use 100% utilization consistently
- **Expected**: Same instance type + same environment = same utilization

**Verdict**: ❌ **This should NOT cause differences within same environment**

### **Hypothesis 2: OS Type Differences**
**Theory**: Different operating systems causing pricing multipliers

**Analysis**:
```
All VMs show "Linux" in Operating System column
Expected OS multipliers:
- Linux: 1.0x (base pricing)
- Windows: 1.4x (+40%)
- RHEL: 1.2x (+20%)
```

**Verdict**: ❌ **All show Linux - should be same multiplier**

### **Hypothesis 3: Pricing Model Application Issues**
**Theory**: Different pricing models being applied incorrectly

**Analysis**:
- **Non-Production**: Should all use "On-Demand"
- **Production**: Should all use "EC2 Instance Savings Plans"
- **CSV Shows**: Correct pricing plans applied

**Verdict**: ❌ **Pricing plans are correctly applied**

### **Hypothesis 4: Regional Pricing Variations**
**Theory**: Different regional pricing being applied

**Analysis**:
- **Region**: All VMs processed for us-east-1
- **Expected**: Same region = same base pricing

**Verdict**: ❌ **All in same region**

### **Hypothesis 5: Calculation Logic Bug**
**Theory**: Bug in cost calculation formulas

**Analysis**: **🚨 MOST LIKELY CAUSE**
- Different VMs getting different hourly rates
- Possible issues in pricing lookup or calculation
- May be related to caching or data retrieval

---

## 🔧 **DETAILED INVESTIGATION NEEDED**

### **Step 1: Examine Pricing Lookup Logic**
Need to investigate:
```python
# In cost calculation service
hourly_rate = await self._get_hourly_rate_for_model(
    instance_pricing, 
    pricing_model, 
    tco_parameters, 
    workload_type
)
```

**Potential Issues**:
- Inconsistent pricing data retrieval
- Caching issues causing stale data
- Different pricing records being selected

### **Step 2: Check Utilization Application**
Need to verify:
```python
# Utilization calculation
if workload_type == WorkloadType.PRODUCTION:
    utilization_percent = tco_parameters.production_utilization_percent  # Should be 100%
else:
    utilization_percent = tco_parameters.non_production_utilization_percent  # Should be 50%
```

**Potential Issues**:
- Workload type misclassification
- Utilization percentage not applied consistently

### **Step 3: Investigate Savings Plans Pricing**
For Production workloads:
```python
# Savings Plans calculation
savings_plans_pricing = await self.pricing_service.get_savings_plans_pricing(
    instance_family,
    tco_parameters.target_region,
    tco_parameters.savings_plan_commitment,
    tco_parameters.savings_plan_payment
)
```

**Potential Issues**:
- Different Savings Plans rates being returned
- Fallback to different pricing models
- Inconsistent discount application

---

## 📊 **EXPECTED vs ACTUAL CALCULATIONS**

### **Non-Production m5.2xlarge (50% utilization)**
```
Expected Calculation:
Base hourly rate: ~$0.384/hour (m5.2xlarge On-Demand)
Monthly hours: 730.56 hours
Utilization: 50% = 365.28 effective hours
Monthly cost: $0.384 × 365.28 = $140.27

Actual Results:
apache95-demo: $143.47 (close to expected)
router-dev-go: $149.07 (higher than expected)
```

### **Production m5.xlarge (100% utilization, Savings Plans)**
```
Expected Calculation:
Base hourly rate: ~$0.192/hour (m5.xlarge On-Demand)
Savings Plans discount: ~30-40%
Discounted rate: ~$0.115-0.134/hour
Monthly hours: 730.56 hours
Utilization: 100% = 730.56 effective hours
Monthly cost: ~$84-98/month

Actual Results:
cms92-dr: $53.86 (lower than expected - good discount)
grafana-archive-dr51: $37.33 (much lower - inconsistent)
```

---

## 🚨 **CRITICAL FINDINGS**

### **1. Inconsistent Pricing Logic**
- Same instance types in same environment should have identical costs
- Current system shows significant variations ($5.60 and $16.53 differences)
- This indicates a fundamental issue in the cost calculation logic

### **2. Potential Root Causes**
1. **Pricing Data Inconsistency**: Different pricing records being retrieved
2. **Calculation Bug**: Formula not applied consistently
3. **Caching Issues**: Stale or incorrect cached pricing data
4. **Workload Classification**: Misclassification affecting utilization/pricing model

### **3. Impact Assessment**
- **User Confidence**: Inconsistent results reduce trust in cost estimates
- **Business Decisions**: Inaccurate costs affect migration planning
- **System Reliability**: Indicates broader calculation reliability issues

---

## 🔧 **RECOMMENDED INVESTIGATION STEPS**

### **Immediate Actions**
1. **Debug Pricing Lookups**: Log actual hourly rates retrieved for each VM
2. **Verify Utilization Application**: Confirm utilization percentages applied
3. **Check Workload Classification**: Ensure consistent environment detection
4. **Validate Savings Plans**: Confirm consistent discount application

### **Diagnostic Script Needed**
```python
# Debug cost calculation for specific VMs
async def debug_cost_calculation(vm_name, instance_type, environment):
    # Log each step of calculation
    # Compare pricing data retrieved
    # Verify utilization and discounts applied
    # Identify source of discrepancy
```

---

## 🎯 **NEXT STEPS**

### **Before Singapore Fix**
1. **Resolve Calculation Inconsistencies**: Fix pricing logic bugs
2. **Validate us-east-1 Accuracy**: Ensure consistent results
3. **Test with Multiple VMs**: Confirm same instance types = same costs

### **After Logic Fix**
1. **Re-test us-east-1**: Verify consistent pricing
2. **Implement Singapore Fix**: Deploy hybrid pricing service
3. **Validate End-to-End**: Ensure both regions work correctly

---

**Status**: 🚨 **CRITICAL ISSUE IDENTIFIED**  
**Priority**: **HIGH** - Fix calculation inconsistencies before Singapore implementation  
**Impact**: Affects cost accuracy for all regions, not just Singapore
