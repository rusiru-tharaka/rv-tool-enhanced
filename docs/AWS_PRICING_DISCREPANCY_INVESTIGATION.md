# AWS Pricing Discrepancy Investigation

## Issue:
CSV export shows $53.86 for m5.xlarge with Compute Savings Plans, but AWS Pricing Calculator shows $70.81/month

## Data Points:
- **Region**: US-East-1
- **Instance**: m5.xlarge
- **Pricing Model**: Compute Savings Plans
- **CSV Output**: $53.86
- **AWS Actual**: $70.81/month
- **Discrepancy**: $16.95 (24% difference)

## Investigation Steps:
1. Check if frontend is using hardcoded/estimated costs instead of real AWS pricing
2. Verify if backend AWS Pricing API integration is working
3. Check if Compute Savings Plans discount is being applied correctly
4. Ensure US-East-1 pricing data is accurate

## Status: INVESTIGATING
