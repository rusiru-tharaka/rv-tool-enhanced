# Singapore TCO Test Calculation - Complete Explanation

**Analysis Date**: July 31, 2025  
**Objective**: Explain how Singapore TCO Test calculates Total Cost of Ownership  
**Location**: `/backend/routers/singapore_tco_test.py`  

---

## 🎯 **OVERVIEW: HOW SINGAPORE TCO WORKS**

The Singapore TCO Test uses a **hardcoded pricing approach** with **real Singapore AWS pricing data** to provide consistent, accurate cost calculations for the ap-southeast-1 region.

### **Key Principle**: 
Instead of relying on dynamic API calls (which can fail or be inconsistent), Singapore TCO uses **pre-validated Singapore pricing data** stored locally to ensure reliable results.

---

## 📊 **STEP-BY-STEP CALCULATION PROCESS**

### **Step 1: VM Data Extraction**
```python
# Extract VM specifications from RVTools data
vm_name = vm_data.get('vm_name', vm_data.get('VM', 'Unknown'))
cpu_cores = int(vm_data.get('cpu_count', vm_data.get('CPUs', 1)))
memory_mb = float(vm_data.get('memory_mb', vm_data.get('Memory', 1024)))
storage_gb = float(vm_data.get('disk_gb', vm_data.get('storage_gb', 0)))

# Convert memory from MB to GB
memory_gb = memory_mb / 1024
```

### **Step 2: Instance Recommendation**
```python
# Use existing recommendation service to get optimal AWS instance type
vm_spec = VMSpecification(
    vm_name=vm_name,
    cpu_cores=cpu_cores,
    memory_gb=memory_gb,
    storage_gb=storage_gb,
    workload_type=WorkloadType.PRODUCTION if 'prod' in vm_name.lower() else WorkloadType.DEVELOPMENT
)

recommendation = recommendation_service.recommend_instance(vm_spec)
instance_type = recommendation.instance_type  # e.g., 't3.xlarge'
```

### **Step 3: Environment Classification**
```python
# Determine if VM is Production or Non-Production based on name
vm_name_lower = vm_name.lower()

if any(indicator in vm_name_lower for indicator in ['prod', 'dr', 'backup', 'archive']):
    environment = 'Production'
elif any(indicator in vm_name_lower for indicator in ['dev', 'test', 'uat', 'demo', 'staging']):
    environment = 'Non-Production'
else:
    # Default based on size (larger VMs assumed to be Production)
    environment = 'Production' if (cpu_cores >= 4 or memory_gb >= 16) else 'Non-Production'
```

### **Step 4: Pricing Model Selection** 🔧 **HARDCODED LOGIC**
```python
if environment == 'Production':
    pricing_key = 'reserved_3y_no_upfront'  # 3-Year Reserved Instance
    pricing_plan = 'Reserved Instance (3 Year)'
    utilization = 1.0  # 100% utilization
else:
    pricing_key = 'on_demand'  # On-Demand pricing
    pricing_plan = 'On-Demand'
    utilization = 0.5  # 50% utilization for non-production
```

### **Step 5: Singapore Pricing Lookup**
```python
# Get hourly rate from hardcoded Singapore pricing data
if instance_type in SINGAPORE_PRICING['instance_pricing']:
    hourly_rate = SINGAPORE_PRICING['instance_pricing'][instance_type][pricing_key]
else:
    # Fallback to m5.xlarge if specific instance type not found
    hourly_rate = SINGAPORE_PRICING['instance_pricing']['m5.xlarge'][pricing_key]
```

### **Step 6: Cost Calculation**
```python
# Calculate monthly costs
hours_per_month = 24 * 30.44  # 730.56 hours (accounting for varying month lengths)

# Instance cost with utilization factor
instance_monthly_cost = hourly_rate * hours_per_month * utilization

# Storage cost (Singapore GP3 pricing)
storage_monthly_cost = storage_gb * SINGAPORE_PRICING['storage_pricing']['gp3']  # $0.092/GB/month

# Total monthly cost
total_monthly_cost = instance_monthly_cost + storage_monthly_cost
```

---

## 💰 **SINGAPORE PRICING DATA STRUCTURE**

### **Instance Pricing** (Sample):
```json
{
  "t3.xlarge": {
    "on_demand": 0.2048,                    // $0.2048/hour
    "reserved_1y_no_upfront": 0.1414,       // $0.1414/hour (1-year RI)
    "reserved_3y_no_upfront": 0.1232        // $0.1232/hour (3-year RI)
  },
  "m5.xlarge": {
    "on_demand": 0.232,                     // $0.232/hour
    "reserved_3y_no_upfront": 0.14          // $0.14/hour (3-year RI)
  }
}
```

### **Storage Pricing**:
```json
{
  "storage_pricing": {
    "gp3": 0.092,    // $0.092 per GB per month
    "gp2": 0.115,    // $0.115 per GB per month
    "io1": 0.138     // $0.138 per GB per month
  }
}
```

---

## 🧮 **EXAMPLE CALCULATION**

### **VM Example**: `apache95-demo`
- **Specs**: 3 CPU, 16 GB RAM, 175.26 GB storage
- **Recommended Instance**: `r5.xlarge` (based on memory requirements)
- **Environment**: Non-Production (no 'prod' in name)

### **Calculation Steps**:
```python
# Step 1: Environment = Non-Production
pricing_key = 'on_demand'
utilization = 0.5  # 50%

# Step 2: Get Singapore pricing for r5.xlarge On-Demand
hourly_rate = 0.304  # $0.304/hour (Singapore On-Demand rate)

# Step 3: Calculate costs
hours_per_month = 730.56
instance_monthly_cost = 0.304 * 730.56 * 0.5 = $111.05
storage_monthly_cost = 175.26 * 0.092 = $16.12
total_monthly_cost = $111.05 + $16.12 = $127.17
```

### **Production VM Example**: `erp-gateway-prod76`
- **Specs**: 4 CPU, 6 GB RAM, 96.69 GB storage
- **Recommended Instance**: `m5.xlarge`
- **Environment**: Production (contains 'prod')

### **Calculation Steps**:
```python
# Step 1: Environment = Production
pricing_key = 'reserved_3y_no_upfront'
utilization = 1.0  # 100%

# Step 2: Get Singapore pricing for m5.xlarge 3-Year RI
hourly_rate = 0.14  # $0.14/hour (Singapore 3-Year RI rate)

# Step 3: Calculate costs
instance_monthly_cost = 0.14 * 730.56 * 1.0 = $102.28
storage_monthly_cost = 96.69 * 0.092 = $8.90
total_monthly_cost = $102.28 + $8.90 = $111.18
```

---

## 🎯 **KEY DIFFERENCES FROM ENHANCED TCO**

### **Singapore TCO Approach**:
- ✅ **Hardcoded Pricing**: Uses pre-validated Singapore rates
- ✅ **Consistent Results**: Same input always produces same output
- ✅ **No API Dependencies**: Works offline, no API failures
- ✅ **Regional Accuracy**: Specifically tuned for Singapore pricing

### **Enhanced TCO Approach**:
- ⚠️ **Dynamic API Calls**: Relies on AWS Pricing API
- ⚠️ **Variable Results**: Can change based on API availability
- ⚠️ **Complex Fallbacks**: Multiple layers of fallback logic
- ⚠️ **Generic Pricing**: May not reflect regional variations

---

## 📊 **CALCULATION FORMULA SUMMARY**

### **For Production VMs**:
```
Monthly Cost = (Singapore_3yr_RI_Rate × 730.56 hours × 100%) + (Storage_GB × $0.092)
```

### **For Non-Production VMs**:
```
Monthly Cost = (Singapore_OnDemand_Rate × 730.56 hours × 50%) + (Storage_GB × $0.092)
```

### **Total TCO**:
```
Total Monthly TCO = Σ(All VM Monthly Costs)
Total Annual TCO = Total Monthly TCO × 12
```

---

## 🔍 **VALIDATION & CONSISTENCY**

### **Consistency Checks**:
The Singapore TCO performs validation to ensure:
1. **Same instance types** in same environment have **same hourly rates**
2. **No calculation errors** in cost computation
3. **All VMs processed** successfully

### **Example Validation**:
```python
# Group VMs by instance type and environment
consistency_check = {}
for vm in vm_costs:
    key = f"{vm['recommendedInstanceType']}_{vm['environment']}"
    consistency_check[key].append(vm['instanceCost'])

# Check for inconsistencies
for key, costs in consistency_check.items():
    if len(set(round(cost, 2) for cost in costs)) > 1:
        # Flag inconsistency for review
        inconsistencies.append({...})
```

---

## 🎉 **WHY SINGAPORE TCO IS RELIABLE**

### **✅ Advantages**:
1. **Predictable Results**: Same input = same output every time
2. **No API Failures**: Works even when AWS APIs are down
3. **Regional Accuracy**: Uses actual Singapore pricing from AWS Calculator
4. **Fast Performance**: No network calls, instant calculations
5. **Easy Debugging**: Clear, traceable calculation steps

### **✅ Use Cases**:
- **Baseline Comparisons**: Reliable reference for cost estimates
- **Proof of Concepts**: Demonstrating cost optimization potential
- **Offline Analysis**: Works without internet connectivity
- **Consistent Reporting**: Same results across different environments

---

## 📋 **SUMMARY**

The Singapore TCO Test calculates costs using:

1. **VM Specifications** → Extract from RVTools data
2. **Instance Recommendations** → Use existing recommendation service  
3. **Environment Classification** → Production vs Non-Production based on VM names
4. **Hardcoded Pricing Logic** → Production uses 3yr RI, Non-Prod uses On-Demand 50%
5. **Singapore Pricing Lookup** → Get rates from local pricing data
6. **Cost Calculation** → Apply utilization and storage costs
7. **Validation** → Ensure consistency across similar VMs

**Result**: Reliable, consistent TCO calculations specifically optimized for Singapore region pricing with proven accuracy for cost estimation and comparison purposes.

The Singapore TCO serves as the **"gold standard"** for validating other TCO calculation methods and ensuring accurate cost projections for AWS migrations in the Singapore region.
