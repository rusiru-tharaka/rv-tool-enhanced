# Pricing Discrepancy Investigation

## Issue Details:
- **RVTool File**: RVTools_Sample_4
- **Export File**: vm-cost-estimates-86b56aeb-24d0-4d92-8749-2f97eee18f10.csv
- **TCO Parameters Used**:
  - Region: Singapore (ap-southeast-1)
  - Pricing Model: EC2 Savings Plans
  - Term: 3 Years
  - Payment: No Upfront
- **Problem**: Discrepancy between exported pricing and real AWS pricing

## Root Causes Identified:

### ✅ Issue 1: Pricing Plan Names (FIXED)
**Problem**: Export showed "On-Demand" instead of "EC2 Savings Plans"
**Root Cause**: `_get_pricing_plan_name()` method was using old pricing logic
**Fix**: Updated method to use enhanced workload-specific pricing parameters
**Result**: Now correctly shows "EC2 Instance Savings Plans"

### ⚠️ Issue 2: AWS Pricing API Problems
**Problem**: Cannot retrieve pricing for some instance types in Singapore
**Root Cause**: AWS Pricing API filtering issues for ap-southeast-1 region
**Evidence**: 
- m5.large: "All filter strategies failed"
- m5.xlarge, m5.2xlarge, t3.small: Missing Reserved Instance pricing
**Impact**: Fallback to On-Demand pricing when Savings Plans pricing unavailable

### ✅ Issue 3: EC2 Savings Plans Discount Calculation (CORRECT)
**Verification**: 28% discount for 3-year no upfront is accurate
**Calculation**: $0.096/hr → $0.0691/hr (28% savings)
**Monthly**: $70.13 → $50.50 (Production), $25.25 (Non-Production at 50% utilization)

## Status: PARTIALLY RESOLVED - Need to fix AWS Pricing API issues
