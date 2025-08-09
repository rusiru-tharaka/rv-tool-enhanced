# Data Discrepancy Analysis - Large Dataset Issues

**Date**: July 28, 2025  
**Dataset**: vm-cost-estimates-7fd7e1e4-83b2-4a98-9a29-c8fc0c8d9381.csv  
**Records**: 2,164 VMs  
**Status**: ❌ **CRITICAL ISSUES IDENTIFIED**  

---

## 🎯 Issues Identified

### **1. ❌ EC2 Instance Size Over-Provisioning**
**Examples from CSV**:
```
VM: PRQMNMS01 - CPU: 2, Memory: 16GB → Recommended: m5.2xlarge (8 vCPU, 32GB)
VM: PRQMSTG04 - CPU: 2, Memory: 16GB → Recommended: m5.2xlarge (8 vCPU, 32GB)  
VM: PRQMTEMP01 - CPU: 2, Memory: 16GB → Recommended: m5.2xlarge (8 vCPU, 32GB)
VM: ENTIDMAINT - CPU: 1, Memory: 2GB → Recommended: t3.small (2 vCPU, 2GB) ✅ This one is correct
```

**Problem**: Most VMs with 2 CPU/16GB are being recommended m5.2xlarge (8 vCPU/32GB) instead of m5.large (2 vCPU/8GB) or m5.xlarge (4 vCPU/16GB)

### **2. ❌ Pricing Plan Not Applied Correctly**
**Evidence from CSV**:
```
All VMs show "Compute Savings Plans" regardless of user selection
Production and Non-Production VMs have identical pricing plans
No differentiation between user-selected pricing preferences
```

**Problem**: User-selected pricing plans (On-Demand, Reserved Instance, Spot) are being ignored

### **3. ❌ Instance Cost Discrepancies**
**Examples of Same Instance Type with Different Costs**:
```
m5.2xlarge instances:
- PRQMCDR01: -$61.08 (NEGATIVE cost!)
- PRQMNMS01: $86.79
- PRQMPRO01: $100.67
- PRQMSTG01: $27.81
- PRQMSTG04: $44.37
```

**Problem**: Same instance type (m5.2xlarge) showing wildly different costs, including negative costs

### **4. ❌ Suspicious Total Cost Pattern**
**Pattern Observed**:
```
m5.2xlarge VMs: Almost all total $115.92
m5.xlarge VMs: Almost all total $57.96  
m5.large VMs: Almost all total $28.98
m5.4xlarge VMs: Almost all total $231.84
```

**Problem**: Total costs appear to be hardcoded rather than calculated based on actual VM requirements

---

## 🔍 Root Cause Analysis

### **Issue 1: Over-Provisioning Logic**
The instance recommendation algorithm is not properly matching VM requirements to AWS instance types.

### **Issue 2: Pricing Plan Override**
The system is defaulting to "Compute Savings Plans" regardless of user selection.

### **Issue 3: Cost Calculation Errors**
Instance costs are being calculated incorrectly, possibly due to:
- Wrong pricing data lookup
- Incorrect formula application
- Storage cost bleeding into instance cost

### **Issue 4: Hardcoded Total Costs**
Total costs appear to be predetermined rather than calculated dynamically.
