# CSV Export Discrepancies Analysis

## Issues Identified:

### 1. **Instance Type Mismatches** ❌
- **apache95-demo**: 3 CPU, 16GB RAM → Recommended m5.2xlarge (8 vCPU, 32GB)
- **auth98-dev**: 1 CPU, 2GB RAM → Recommended t3.small (2 vCPU, 2GB) 
- **router-dev-go**: 8 CPU, 8GB RAM → Recommended m5.2xlarge (8 vCPU, 32GB)

### 2. **Cost Calculation Issues** ❌
- **Inconsistent pricing**: Same instance types showing different costs
- **Storage cost calculation**: Appears to be using $0.10/GB instead of Singapore pricing
- **Instance cost calculation**: Not matching actual Singapore On-Demand rates

### 3. **Environment Classification Issues** ❌
- **auth98-dev**: Correctly classified as Non-Production ✅
- **router-dev-go**: Correctly classified as Non-Production ✅
- **tomcat55-uat**: Should be Non-Production but shows Production ❌

### 4. **Pricing Plan** ✅
- All showing "On-Demand" as expected

## Root Causes:
1. Frontend cost calculation using hardcoded values instead of real pricing
2. Instance recommendation logic not properly sizing instances
3. Environment detection logic needs refinement
4. Storage pricing not using Singapore rates

## Status: INVESTIGATING FIXES
