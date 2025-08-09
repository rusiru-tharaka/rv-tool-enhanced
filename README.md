# RVTool Enhanced UX Platform

A comprehensive AI-powered platform for analyzing VMware RVTools exports and providing AWS migration cost optimization recommendations.

## 🎯 Project Status: PRODUCTION READY ✅

**Latest Update**: Migrated to clean project structure with proper organization and deployment automation.

## 🏗️ Architecture

### Core Components
- **Frontend**: React.js with TypeScript and Vite
- **Backend**: FastAPI with modular router architecture
- **Database**: PostgreSQL with Alembic migrations
- **Deployment**: AWS ECS, S3, CloudFront with automated deployment
- **AI**: Amazon Bedrock integration for cost optimization

## 📁 Project Structure

```
rv-tool-enhanced/
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── database.py          # Database configuration
│   │   ├── routers/             # API route modules
│   │   ├── services/            # Business logic services
│   │   ├── models/              # Data models and schemas
│   │   └── utils/               # Utility functions
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Backend tests
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Container configuration
├── frontend/
│   ├── src/                     # React application source
│   ├── package.json             # Node.js dependencies
│   ├── vite.config.ts           # Build configuration
│   └── tailwind.config.js       # CSS framework config
├── deployment/
│   ├── scripts/                 # Deployment automation
│   ├── aws/                     # AWS configurations
│   └── docker/                  # Docker configurations
├── docs/                        # Documentation
└── scripts/                     # Development scripts
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional)
- AWS CLI configured

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
```

### Development (Background Mode)
```bash
# Start development servers in background
./scripts/start-dev.sh

# Check server status
./scripts/status-dev.sh

# Stop development servers
./scripts/stop-dev.sh

# View logs
tail -f logs/backend_dev.log
tail -f logs/frontend_dev.log
```

### Development (Manual Mode)
```bash
# Start backend (from backend directory)
cd backend
source venv/bin/activate
uvicorn app.simple_main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (from frontend directory)
cd frontend
npm run dev
```

## 🚀 Deployment

### Full Application Deployment
```bash
cd deployment/scripts
./deploy-full-application.sh
```

### Individual Component Deployment
```bash
# Backend only
./deploy-backend-to-aws.sh

# Frontend only
./deploy-frontend-to-aws.sh
```

## 🌐 Access Points

### Production URLs
- **Frontend**: https://d1gojl4pm0o47c.cloudfront.net
- **Backend API**: http://rvtool-alb-dev-1648331028.us-east-1.elb.amazonaws.com

### Development URLs
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Key Features

- ✅ **File Upload & Processing**: Handle large RVTools.xlsx files
- ✅ **4-Phase Migration Analysis**: Comprehensive migration planning
- ✅ **Cost Optimization**: AI-powered recommendations
- ✅ **Multi-Region Support**: Global AWS pricing analysis
- ✅ **Reserved Instance Planning**: RI optimization strategies
- ✅ **Savings Plans Integration**: Cost optimization planning
- ✅ **Spot Instance Analysis**: Cost-effective compute options
- ✅ **PDF Report Generation**: Professional migration reports
- ✅ **CSV Export**: Detailed data export capabilities

## 📊 Migration Phases

1. **Phase 1**: Infrastructure Assessment & Baseline
2. **Phase 2**: Cost Optimization (RI, Savings Plans, Spot)
3. **Phase 3**: Modernization Recommendations
4. **Phase 4**: Migration Execution Planning

## 🔐 Security Features

- IAM roles with least privilege access
- VPC with private subnets
- Security groups with restricted access
- Secrets Manager for credentials
- S3 bucket policies for secure storage

## 📈 Monitoring & Observability

- CloudWatch logs for all components
- Health check endpoints
- ECS service metrics and alarms
- Application performance insights

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues, questions, or feature requests:
1. Check the documentation in `/docs`
2. Review deployment guides
3. Create an issue in the repository

---

**Status**: ✅ Production Ready | **Version**: 2.0.0 | **Last Updated**: August 5, 2025
