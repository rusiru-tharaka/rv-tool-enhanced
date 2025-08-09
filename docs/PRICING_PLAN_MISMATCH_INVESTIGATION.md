# Pricing Plan Mismatch Investigation

## Issue:
Regardless of TCO parameter selection (e.g., EC2 Savings Plans), CSV export always shows "On-Demand" in Pricing Plan column

## Investigation Steps:
1. Check how TCO parameters are passed to cost calculation
2. Verify how pricing plan is determined and stored in cost estimates
3. Check if frontend CSV export is using correct pricing plan data
4. Ensure backend cost calculation properly applies selected pricing model
5. Fix the disconnect between TCO parameters and displayed pricing plan

## Status: INVESTIGATING
