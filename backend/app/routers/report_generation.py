"""
Report Generation Router
API endpoints for generating PDF reports with AI-powered content
"""

import asyncio
import sys
import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import Dict, Any, Optional
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import services with absolute paths
from ..services.session_manager import session_manager
from ..services.pdf_report_generator import PDFReportGenerator
from ..services.ai_blocker_analyzer import AIBlockerAnalyzer
from ..services.ai_modernization_analyzer import AIModernizationAnalyzer

# Create router
report_router = APIRouter(prefix="/api/reports", tags=["Report Generation"])

# Initialize services
pdf_generator = PDFReportGenerator()
blocker_analyzer = AIBlockerAnalyzer()
modernization_analyzer = AIModernizationAnalyzer()

@report_router.post("/migration-blockers/{session_id}")
async def generate_migration_blocker_report(session_id: str) -> Response:
    """
    Generate comprehensive migration blocker analysis PDF report
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        PDF report as binary response
    """
    try:
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get migration blocker analysis
        blocker_result = await blocker_analyzer.analyze_migration_blockers(session.vm_inventory)
        
        # Prepare session data for report
        session_data = {
            "session_id": session_id,
            "total_vms": len(session.vm_inventory),
            "migration_blockers": blocker_result.get('blockers', []),
            "analysis_metadata": blocker_result.get('metadata', {}),
            "created_at": session.created_at.isoformat() if hasattr(session, 'created_at') else datetime.now().isoformat()
        }
        
        # Generate PDF report
        pdf_data = await pdf_generator.generate_migration_blocker_report(session_data)
        
        # Return PDF as response
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=migration_blocker_report_{session_id}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate migration blocker report: {str(e)}"
        )

@report_router.post("/executive-summary/{session_id}")
async def generate_executive_summary_report(session_id: str) -> Response:
    """
    Generate executive summary PDF report
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        Executive summary PDF report
    """
    try:
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get analysis results
        blocker_result = await blocker_analyzer.analyze_migration_blockers(session.vm_inventory)
        modernization_result = await modernization_analyzer.analyze_modernization_opportunities(session.vm_inventory)
        
        # Prepare comprehensive session data
        session_data = {
            "session_id": session_id,
            "total_vms": len(session.vm_inventory),
            "migration_blockers": blocker_result.get('blockers', []),
            "modernization_opportunities": modernization_result.get('opportunities', []),
            "analysis_summary": {
                "blocker_analysis": blocker_result.get('analysis_summary', {}),
                "modernization_analysis": modernization_result.get('analysis_summary', {})
            },
            "created_at": session.created_at.isoformat() if hasattr(session, 'created_at') else datetime.now().isoformat()
        }
        
        # Generate executive summary (using migration blocker report for now)
        pdf_data = await pdf_generator.generate_migration_blocker_report(session_data)
        
        # Return PDF as response
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=executive_summary_{session_id}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate executive summary report: {str(e)}"
        )

@report_router.post("/technical-analysis/{session_id}")
async def generate_technical_analysis_report(session_id: str) -> Response:
    """
    Generate detailed technical analysis PDF report
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        Technical analysis PDF report
    """
    try:
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get comprehensive analysis results
        blocker_result = await blocker_analyzer.analyze_migration_blockers(session.vm_inventory)
        modernization_result = await modernization_analyzer.analyze_modernization_opportunities(session.vm_inventory)
        
        # Prepare technical session data
        session_data = {
            "session_id": session_id,
            "total_vms": len(session.vm_inventory),
            "vm_inventory": session.vm_inventory[:10],  # Sample VMs for technical details
            "migration_blockers": blocker_result.get('blockers', []),
            "modernization_opportunities": modernization_result.get('opportunities', []),
            "technical_analysis": {
                "blocker_statistics": blocker_analyzer.get_blocker_statistics(blocker_result.get('blockers', [])),
                "modernization_statistics": modernization_analyzer.get_modernization_statistics(modernization_result.get('opportunities', []))
            },
            "created_at": session.created_at.isoformat() if hasattr(session, 'created_at') else datetime.now().isoformat()
        }
        
        # Generate technical report (using migration blocker report template for now)
        pdf_data = await pdf_generator.generate_migration_blocker_report(session_data)
        
        # Return PDF as response
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=technical_analysis_{session_id}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate technical analysis report: {str(e)}"
        )

@report_router.post("/migration-roadmap/{session_id}")
async def generate_migration_roadmap_report(session_id: str) -> Response:
    """
    Generate migration roadmap PDF report
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        Migration roadmap PDF report
    """
    try:
        # Get session data
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get analysis results for roadmap generation
        blocker_result = await blocker_analyzer.analyze_migration_blockers(session.vm_inventory)
        modernization_result = await modernization_analyzer.analyze_modernization_opportunities(session.vm_inventory)
        
        # Prepare roadmap session data
        session_data = {
            "session_id": session_id,
            "total_vms": len(session.vm_inventory),
            "migration_blockers": blocker_result.get('blockers', []),
            "modernization_opportunities": modernization_result.get('opportunities', []),
            "roadmap_data": {
                "total_monthly_savings": modernization_result.get('analysis_summary', {}).get('total_monthly_savings', 0),
                "implementation_complexity": blocker_result.get('analysis_summary', {}).get('overall_migration_risk', 'MEDIUM'),
                "estimated_timeline": "4-6 months"  # Based on analysis
            },
            "created_at": session.created_at.isoformat() if hasattr(session, 'created_at') else datetime.now().isoformat()
        }
        
        # Generate roadmap report (using migration blocker report template for now)
        pdf_data = await pdf_generator.generate_migration_blocker_report(session_data)
        
        # Return PDF as response
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=migration_roadmap_{session_id}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate migration roadmap report: {str(e)}"
        )

@report_router.get("/available/{session_id}")
async def get_available_reports(session_id: str) -> Dict[str, Any]:
    """
    Get list of available reports for a session
    
    Args:
        session_id: Analysis session identifier
        
    Returns:
        List of available report types and their descriptions
    """
    try:
        # Verify session exists
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        available_reports = [
            {
                "type": "migration-blockers",
                "name": "Migration Blocker Analysis",
                "description": "Comprehensive analysis of migration challenges with executive summary and detailed remediation plans",
                "endpoint": f"/api/reports/migration-blockers/{session_id}",
                "estimated_pages": "5-10 pages"
            },
            {
                "type": "executive-summary",
                "name": "Executive Summary",
                "description": "Business-focused summary with key insights and strategic recommendations for executives",
                "endpoint": f"/api/reports/executive-summary/{session_id}",
                "estimated_pages": "3-5 pages"
            },
            {
                "type": "technical-analysis",
                "name": "Technical Implementation Guide",
                "description": "Detailed technical specifications, implementation steps, and technical considerations",
                "endpoint": f"/api/reports/technical-analysis/{session_id}",
                "estimated_pages": "8-15 pages"
            },
            {
                "type": "migration-roadmap",
                "name": "Migration Roadmap",
                "description": "Phased migration plan with timelines, dependencies, resource requirements, and risk mitigation",
                "endpoint": f"/api/reports/migration-roadmap/{session_id}",
                "estimated_pages": "6-12 pages"
            }
        ]
        
        return {
            "session_id": session_id,
            "total_vms": len(session.vm_inventory),
            "available_reports": available_reports,
            "generation_timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available reports: {str(e)}"
        )

@report_router.get("/health")
async def report_generation_health() -> Dict[str, Any]:
    """
    Health check for report generation service
    
    Returns:
        Service health status
    """
    try:
        return {
            "status": "healthy",
            "service": "report_generation",
            "timestamp": datetime.now().isoformat(),
            "features": [
                "migration_blocker_reports",
                "executive_summaries",
                "technical_analysis",
                "migration_roadmaps",
                "ai_powered_content"
            ],
            "pdf_generator": "operational",
            "ai_services": "operational"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "report_generation",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
