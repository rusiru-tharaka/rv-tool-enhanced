# CSV Export Discrepancy Analysis

**Date**: July 31, 2025  
**CSV File**: `vm-cost-estimates-a17a86f3-91a0-477a-975e-d0a78aab36dc.csv`  
**Status**: 🚨 **CRITICAL DISCREPANCIES IDENTIFIED**  

---

## 🎯 **ANALYSIS OBJECTIVE**

Analyze the CSV export to identify discrepancies in:
1. VM Cost calculations
2. Over-provisioned instance sizes (incorrect sizing)
3. Total cost calculations

---

## 🚨 **CRITICAL DISCREPANCIES FOUND**

### **1. INSTANCE SIZING ISSUES - OVER-PROVISIONED**

| VM Name | Current Specs | Recommended Instance | Issue |
|---------|---------------|---------------------|-------|
| **apache95-demo** | 3 CPU, 16 GB RAM | **m5.2xlarge** (8 vCPU, 32 GB) | ❌ **OVER-PROVISIONED** - 2.67x CPU, 2x RAM |
| **auth98-dev** | 1 CPU, 2 GB RAM | **t3.small** (2 vCPU, 2 GB) | ❌ **OVER-PROVISIONED** - 2x CPU |
| **router-dev-go** | 8 CPU, 8 GB RAM | **m5.2xlarge** (8 vCPU, 32 GB) | ❌ **OVER-PROVISIONED** - 4x RAM |
| **cms92-dr** | 4 CPU, 8 GB RAM | **m5.xlarge** (4 vCPU, 16 GB) | ❌ **OVER-PROVISIONED** - 2x RAM |
| **sync-lb-demo** | 4 CPU, 32 GB RAM | **m5.4xlarge** (16 vCPU, 64 GB) | ❌ **OVER-PROVISIONED** - 4x CPU, 2x RAM |
| **grafana-archive-dr51** | 4 CPU, 8 GB RAM | **m5.xlarge** (4 vCPU, 16 GB) | ❌ **OVER-PROVISIONED** - 2x RAM |
| **subscriber-demo-kafka** | 4 CPU, 8 GB RAM | **m5.xlarge** (4 vCPU, 16 GB) | ❌ **OVER-PROVISIONED** - 2x RAM |
| **tomcat55-uat** | 2 CPU, 8 GB RAM | **m5.xlarge** (4 vCPU, 16 GB) | ❌ **OVER-PROVISIONED** - 2x CPU, 2x RAM |

### **2. COST CALCULATION DISCREPANCIES**

#### **Instance Cost vs Total Cost Mismatches**:

| VM Name | Instance Cost | Storage Cost | Calculated Total | Reported Total | Discrepancy |
|---------|---------------|--------------|------------------|----------------|-------------|
| **apache95-demo** | $143.47 | $17.53 | **$161.00** | $161.00 | ✅ Correct |
| **auth98-dev** | $17.51 | $5.49 | **$23.00** | $23.00 | ✅ Correct |
| **router-dev-go** | $149.07 | $11.93 | **$161.00** | $161.00 | ✅ Correct |
| **cms92-dr** | $44.20 | $4.10 | **$48.30** | $48.30 | ✅ Correct |
| **sync-lb-demo** | $286.81 | $35.19 | **$322.00** | $322.00 | ✅ Correct |
| **grafana-archive-dr51** | $27.67 | $20.63 | **$48.30** | $48.30 | ✅ Correct |
| **subscriber-demo-kafka** | $58.33 | $22.17 | **$80.50** | $80.50 | ✅ Correct |
| **tomcat55-uat** | $77.60 | $2.90 | **$80.50** | $80.50 | ✅ Correct |

**Note**: Total cost calculations are mathematically correct, but the underlying instance costs are inflated due to over-provisioning.

### **3. STORAGE COST CALCULATION**

**Formula Used**: Storage Cost = Storage GB × $0.10/GB/month

| VM Name | Storage (GB) | Expected Storage Cost | Reported Storage Cost | Status |
|---------|--------------|----------------------|---------------------|---------|
| apache95-demo | 175.26 | $17.53 | $17.53 | ✅ Correct |
| auth98-dev | 54.88 | $5.49 | $5.49 | ✅ Correct |
| router-dev-go | 119.32 | $11.93 | $11.93 | ✅ Correct |
| cms92-dr | 40.97 | $4.10 | $4.10 | ✅ Correct |
| sync-lb-demo | 351.94 | $35.19 | $35.19 | ✅ Correct |
| grafana-archive-dr51 | 206.27 | $20.63 | $20.63 | ✅ Correct |
| subscriber-demo-kafka | 221.73 | $22.17 | $22.17 | ✅ Correct |
| tomcat55-uat | 28.97 | $2.90 | $2.90 | ✅ Correct |

---

## 🔍 **ROOT CAUSE ANALYSIS**

### **Primary Issue: Instance Recommendation Algorithm**

The instance recommendation service is systematically over-provisioning instances:

1. **CPU Over-provisioning**: Recommending instances with more vCPUs than needed
2. **Memory Over-provisioning**: Recommending instances with significantly more RAM than current usage
3. **Instance Family Selection**: Not optimizing for cost-effective instance types

### **Examples of Over-provisioning**:

#### **Case 1: apache95-demo**
- **Current**: 3 vCPU, 16 GB RAM
- **Recommended**: m5.2xlarge (8 vCPU, 32 GB RAM)
- **Better Option**: m5.xlarge (4 vCPU, 16 GB RAM) - would save ~$70/month

#### **Case 2: auth98-dev**
- **Current**: 1 vCPU, 2 GB RAM
- **Recommended**: t3.small (2 vCPU, 2 GB RAM)
- **Better Option**: t3.micro (2 vCPU, 1 GB RAM) or t3.nano - would save ~$8/month

#### **Case 3: sync-lb-demo**
- **Current**: 4 vCPU, 32 GB RAM
- **Recommended**: m5.4xlarge (16 vCPU, 64 GB RAM)
- **Better Option**: m5.2xlarge (8 vCPU, 32 GB RAM) - would save ~$140/month

---

## 💰 **COST IMPACT ANALYSIS**

### **Total Monthly Cost Impact**:
- **Current Reported Total**: $924.60/month
- **Estimated Optimized Cost**: ~$650-700/month
- **Potential Savings**: $200-270/month (22-29% reduction)

### **Annual Impact**:
- **Potential Annual Savings**: $2,400-3,240/year

---

## 🎯 **SPECIFIC ISSUES IDENTIFIED**

### **1. Instance Recommendation Logic**:
- Algorithm appears to round up significantly rather than right-sizing
- Not considering cost optimization in recommendations
- May be using outdated or overly conservative sizing rules

### **2. Instance Type Selection**:
- Heavy bias toward m5 family instances
- Not considering t3/t3a instances for low-utilization workloads
- Not optimizing for workload-specific instance types

### **3. Memory-to-CPU Ratio Issues**:
- Many VMs have low memory requirements but get high-memory instances
- Not considering memory-optimized vs compute-optimized instances appropriately

---

## 🔧 **RECOMMENDED FIXES**

### **1. Instance Recommendation Service**:
- Implement right-sizing algorithm with 10-20% headroom instead of 2x-4x
- Add cost optimization as primary factor in recommendations
- Consider workload patterns and utilization metrics

### **2. Instance Type Optimization**:
- Expand instance type selection to include t3, t3a, m5a, c5, r5 families
- Implement workload-specific instance type selection
- Add burstable instance recommendations for low-utilization workloads

### **3. Cost Calculation Accuracy**:
- Verify pricing data for recommended instances
- Implement cost comparison between multiple instance options
- Add cost optimization recommendations in the UI

---

## 📊 **NEXT STEPS**

1. **Investigate Instance Recommendation Service**: Check the algorithm logic
2. **Verify Pricing Data**: Ensure accurate AWS pricing information
3. **Implement Right-sizing Logic**: Reduce over-provisioning
4. **Add Cost Optimization**: Include multiple instance options with cost comparison
5. **Update UI**: Show cost optimization opportunities to users

---

**Status**: 🚨 **CRITICAL ISSUES IDENTIFIED - IMMEDIATE ACTION REQUIRED**

The CSV export reveals systematic over-provisioning leading to inflated cost estimates. This significantly impacts the accuracy and value of the TCO analysis.
