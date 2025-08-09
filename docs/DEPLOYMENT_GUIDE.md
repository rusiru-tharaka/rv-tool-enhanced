# RVTool Enhanced UX - AWS Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the RVTool Enhanced UX Platform to AWS. The deployment includes both the FastAPI backend and React frontend components.

## Architecture

### Current AWS Infrastructure
- **Networking**: VPC, subnets, security groups (RVTool-Networking-dev)
- **Security**: IAM roles and policies (RVTool-Security-dev)
- **Database**: PostgreSQL RDS (RVTool-Database-dev)
- **Compute**: ECS Cluster + ALB (RVTool-Compute-dev)
- **Storage**: S3 buckets + CloudFront (RVTool-Storage-dev)

### Application Components
- **Backend**: FastAPI application with enhanced features
- **Frontend**: React + Vite application with TypeScript
- **Database**: PostgreSQL for data persistence
- **Storage**: S3 for file uploads and static assets
- **CDN**: CloudFront for global content delivery

## Prerequisites

### System Requirements
- AWS CLI configured with `smartslot` profile
- Docker installed and running
- Node.js 18+ and npm
- Bash shell environment

### AWS Permissions
Ensure your AWS profile has permissions for:
- ECS (task definitions, services, clusters)
- ECR (repository access, image push/pull)
- S3 (bucket operations, object upload/download)
- CloudFront (distribution management, invalidations)
- Application Load Balancer (describe operations)
- IAM (assume roles for ECS tasks)

## Deployment Options

### Option 1: Full Automated Deployment (Recommended)
Deploy both backend and frontend with comprehensive testing:

```bash
cd /home/ubuntu/rvtool/enhanced-ux
./deploy-full-application.sh
```

### Option 2: Individual Component Deployment

#### Backend Only
```bash
cd /home/ubuntu/rvtool/enhanced-ux
./deploy-backend-to-aws.sh
```

#### Frontend Only
```bash
cd /home/ubuntu/rvtool/enhanced-ux
./deploy-frontend-to-aws.sh
```

## Deployment Process

### Phase 1: Pre-Deployment Validation
- ✅ Verify AWS connectivity and permissions
- ✅ Validate existing infrastructure components
- ✅ Check application code and dependencies
- ✅ Create deployment backup for rollback

### Phase 2: Backend Deployment
- 🏗️ Build Docker image with enhanced FastAPI application
- 📦 Push image to ECR repository
- 📋 Update ECS task definition with new image
- 🚀 Deploy to ECS service with zero-downtime
- ✅ Verify health checks and service stability

### Phase 3: Frontend Deployment
- ⚙️ Configure production environment variables
- 🏗️ Build React application with Vite
- ☁️ Upload static assets to S3 bucket
- 🔄 Invalidate CloudFront cache for immediate updates
- ✅ Verify frontend accessibility and API connectivity

### Phase 4: Integration Testing
- 🧪 End-to-end connectivity tests
- 📊 Performance validation
- 🔍 Security verification
- 📋 Generate deployment report

## Configuration

### Environment Variables

#### Backend (Production)
```bash
ENVIRONMENT=production
AWS_DEFAULT_REGION=us-east-1
LOG_LEVEL=info
WORKERS=2
```

#### Frontend (Production)
```bash
VITE_API_BASE_URL=http://[ALB_DNS]
VITE_APP_TITLE=RVTool Migration Analysis Platform
VITE_APP_VERSION=2.0.0-production
VITE_ENVIRONMENT=production
VITE_AWS_REGION=us-east-1
```

### Infrastructure Resources

#### Existing Resources (Used by Deployment)
- **ECS Cluster**: `rvtool-cluster-dev`
- **ECS Service**: `rvtool-api-dev`
- **ECR Repository**: `rvtool-api`
- **S3 Bucket**: `rvtool-static-dev-783764609930-202507111752`
- **CloudFront Distribution**: `EL1JB6MBCPLCI`
- **Load Balancer**: `rvtool-alb-dev`

## Post-Deployment

### Access Points
After successful deployment, the application will be available at:

- **Primary Frontend**: `https://[CLOUDFRONT_DOMAIN]`
- **Backend API**: `http://[ALB_DNS]`
- **API Documentation**: `http://[ALB_DNS]/docs`
- **Health Check**: `http://[ALB_DNS]/health`

### Monitoring and Logging
- **ECS Logs**: CloudWatch Logs `/ecs/rvtool-api-dev`
- **Application Metrics**: CloudWatch ECS metrics
- **Frontend Metrics**: CloudFront metrics
- **Custom Metrics**: Application-specific metrics

### Security Considerations
- Backend runs in private subnets with ALB frontend
- S3 bucket configured with CloudFront OAC
- ECS tasks use IAM roles for AWS service access
- Security groups restrict network access appropriately

## Troubleshooting

### Common Issues

#### Backend Deployment Failures
```bash
# Check ECS service status
aws ecs describe-services --cluster rvtool-cluster-dev --services rvtool-api-dev --profile smartslot

# Check task logs
aws logs tail /ecs/rvtool-api-dev --follow --profile smartslot
```

#### Frontend Deployment Issues
```bash
# Check S3 bucket contents
aws s3 ls s3://rvtool-static-dev-783764609930-202507111752 --profile smartslot

# Check CloudFront distribution status
aws cloudfront get-distribution --id EL1JB6MBCPLCI --profile smartslot
```

#### Connectivity Issues
```bash
# Test backend health
curl -v http://[ALB_DNS]/health

# Test frontend
curl -v https://[CLOUDFRONT_DOMAIN]
```

### Rollback Procedures

#### Automatic Rollback
Each deployment creates a backup directory with rollback scripts:
```bash
cd deployment_backup_[TIMESTAMP]
./rollback.sh
```

#### Manual Rollback
```bash
# Rollback ECS service to previous task definition
aws ecs update-service \
    --cluster rvtool-cluster-dev \
    --service rvtool-api-dev \
    --task-definition rvtool-api-dev:[PREVIOUS_REVISION] \
    --profile smartslot
```

## Maintenance

### Regular Updates
1. **Code Updates**: Use deployment scripts for new releases
2. **Security Patches**: Update base Docker images regularly
3. **Dependency Updates**: Keep npm and pip dependencies current
4. **Infrastructure Updates**: Review and update CloudFormation stacks

### Scaling Considerations
- **ECS Auto Scaling**: Configured based on CPU utilization
- **CloudFront**: Automatically scales globally
- **Database**: Monitor RDS performance and scale as needed
- **S3**: Automatically scales with usage

## Support

### Deployment Artifacts
Each deployment generates:
- **Deployment Log**: `deployment_[TIMESTAMP].log`
- **Backup Directory**: `deployment_backup_[TIMESTAMP]/`
- **Deployment Report**: `deployment_report_[TIMESTAMP].md`

### Contact Information
For deployment issues or questions:
1. Check deployment logs and reports
2. Review AWS CloudWatch logs
3. Consult this deployment guide
4. Contact the development team

## Advanced Configuration

### Custom Domain Setup
To configure a custom domain:
1. Create Route 53 hosted zone
2. Request SSL certificate via ACM
3. Update CloudFront distribution
4. Configure DNS records

### SSL/TLS Configuration
- CloudFront supports SSL termination
- Backend communication via ALB (HTTP internal)
- Consider end-to-end encryption for sensitive data

### Performance Optimization
- CloudFront caching policies configured
- S3 static asset optimization
- ECS task resource allocation tuned
- Database connection pooling enabled

---

## Quick Reference

### Deployment Commands
```bash
# Full deployment
./deploy-full-application.sh

# Backend only
./deploy-backend-to-aws.sh

# Frontend only
./deploy-frontend-to-aws.sh
```

### Key AWS Resources
- **ECS Cluster**: rvtool-cluster-dev
- **S3 Bucket**: rvtool-static-dev-783764609930-202507111752
- **CloudFront**: EL1JB6MBCPLCI
- **Load Balancer**: rvtool-alb-dev

### Important Files
- `app_enhanced.py` - Main backend application
- `package.json` - Frontend dependencies
- `Dockerfile` - Backend container configuration
- `vite.config.ts` - Frontend build configuration

---

*This deployment guide is maintained as part of the RVTool Enhanced UX Platform documentation.*
