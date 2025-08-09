"""
PDF Report Generation Service
Creates professional PDF reports for migration analysis with AI-generated content
"""

import io
import json
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# ReportLab imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from .ai_service_wrapper import AIServiceWrapper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFReportGenerator:
    """Professional PDF report generator with AI-powered content"""
    
    def __init__(self, profile_name: str = "smartslot", region: str = "us-east-1"):
        """Initialize PDF report generator"""
        self.ai_service = AIServiceWrapper(profile_name=profile_name, region=region)
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        logger.info("✅ PDF Report Generator initialized")
    
    def _setup_custom_styles(self):
        """Set up custom styles for professional reports"""
        
        # Title style
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1f2937')
        )
        
        # Subtitle style
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#374151')
        )
        
        # Section header style
        self.section_style = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#1f2937'),
            borderWidth=1,
            borderColor=colors.HexColor('#e5e7eb'),
            borderPadding=5
        )
        
        # Body text style
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor('#374151')
        )
        
        # Bullet point style
        self.bullet_style = ParagraphStyle(
            'BulletPoint',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=20,
            bulletIndent=10,
            textColor=colors.HexColor('#4b5563')
        )
        
        # Executive summary style
        self.executive_style = ParagraphStyle(
            'ExecutiveSummary',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=15,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor('#1f2937'),
            backColor=colors.HexColor('#f9fafb'),
            borderWidth=1,
            borderColor=colors.HexColor('#d1d5db'),
            borderPadding=10
        )
    
    async def generate_migration_blocker_report(self, session_data: Dict) -> bytes:
        """Generate comprehensive migration blocker PDF report"""
        
        logger.info("🔍 Generating migration blocker report...")
        
        # Generate AI content
        executive_summary = await self._generate_executive_summary(session_data)
        remediation_overview = await self._generate_remediation_overview(session_data)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Title page
        story.extend(self._create_title_page(session_data))
        story.append(PageBreak())
        
        # Executive Summary
        story.extend(self._create_executive_summary_section(executive_summary))
        
        # Blocker Summary
        story.extend(self._create_blocker_summary_section(session_data))
        
        # Detailed Remediation Plans
        story.extend(self._create_remediation_section(session_data, remediation_overview))
        
        # Individual Blocker Details
        story.extend(self._create_detailed_blockers_section(session_data))
        
        # Recommendations and Next Steps
        story.extend(self._create_recommendations_section(session_data))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        logger.info("✅ Migration blocker report generated successfully")
        return buffer.getvalue()
    
    def _create_title_page(self, session_data: Dict) -> List:
        """Create professional title page"""
        
        story = []
        
        # Main title
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph("Migration Blocker Analysis Report", self.title_style))
        story.append(Spacer(1, 0.5*inch))
        
        # Subtitle
        total_vms = session_data.get('total_vms', 0)
        total_blockers = len(session_data.get('migration_blockers', []))
        
        subtitle = f"Comprehensive Analysis of {total_vms} Virtual Machines<br/>{total_blockers} Migration Challenges Identified"
        story.append(Paragraph(subtitle, self.subtitle_style))
        story.append(Spacer(1, 1*inch))
        
        # Report metadata
        report_date = datetime.now().strftime("%B %d, %Y")
        session_id = session_data.get('session_id', 'Unknown')
        
        metadata_table = Table([
            ['Report Date:', report_date],
            ['Session ID:', session_id],
            ['Analysis Type:', 'AI-Powered Migration Assessment'],
            ['Report Version:', '1.0']
        ], colWidths=[2*inch, 3*inch])
        
        metadata_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb'))
        ]))
        
        story.append(metadata_table)
        story.append(Spacer(1, 1*inch))
        
        # Disclaimer
        disclaimer = """
        This report contains AI-generated analysis and recommendations based on the provided 
        VM inventory data. All recommendations should be validated in a test environment 
        before implementation in production systems.
        """
        story.append(Paragraph(disclaimer, self.body_style))
        
        return story
    
    def _create_executive_summary_section(self, executive_summary: str) -> List:
        """Create executive summary section"""
        
        story = []
        
        story.append(Paragraph("Executive Summary", self.subtitle_style))
        story.append(Paragraph(executive_summary, self.executive_style))
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_blocker_summary_section(self, session_data: Dict) -> List:
        """Create blocker summary with charts"""
        
        story = []
        blockers = session_data.get('migration_blockers', [])
        
        story.append(Paragraph("Migration Blocker Summary", self.subtitle_style))
        
        # Summary statistics
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for blocker in blockers:
            severity = blocker.get('severity', 'medium').lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Summary table
        summary_data = [
            ['Severity Level', 'Count', 'Percentage'],
            ['Critical', severity_counts['critical'], f"{(severity_counts['critical']/len(blockers)*100):.1f}%" if blockers else "0%"],
            ['High', severity_counts['high'], f"{(severity_counts['high']/len(blockers)*100):.1f}%" if blockers else "0%"],
            ['Medium', severity_counts['medium'], f"{(severity_counts['medium']/len(blockers)*100):.1f}%" if blockers else "0%"],
            ['Low', severity_counts['low'], f"{(severity_counts['low']/len(blockers)*100):.1f}%" if blockers else "0%"],
            ['Total', len(blockers), '100%']
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f9fafb'))
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_remediation_section(self, session_data: Dict, remediation_overview: str) -> List:
        """Create intelligent remediation planning section"""
        
        story = []
        
        story.append(Paragraph("Intelligent Remediation Planning", self.subtitle_style))
        story.append(Paragraph(remediation_overview, self.body_style))
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_detailed_blockers_section(self, session_data: Dict) -> List:
        """Create detailed blocker analysis section"""
        
        story = []
        blockers = session_data.get('migration_blockers', [])
        
        story.append(Paragraph("Detailed Blocker Analysis", self.subtitle_style))
        
        # Sort blockers by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_blockers = sorted(blockers, key=lambda x: severity_order.get(x.get('severity', 'medium').lower(), 2))
        
        for i, blocker in enumerate(sorted_blockers[:10]):  # Top 10 blockers
            story.extend(self._create_blocker_detail_section(blocker, i+1))
        
        return story
    
    def _create_blocker_detail_section(self, blocker: Dict, index: int) -> List:
        """Create detailed section for individual blocker"""
        
        story = []
        
        # Blocker header
        vm_name = blocker.get('vm_name', 'Unknown')
        severity = blocker.get('severity', 'medium').title()
        
        header = f"Blocker #{index}: {vm_name} ({severity} Priority)"
        story.append(Paragraph(header, self.section_style))
        
        # Blocker details table
        details_data = [
            ['VM Name:', vm_name],
            ['Severity:', severity],
            ['Issue Type:', blocker.get('issue_type', 'Unknown')],
            ['Description:', blocker.get('description', 'No description available')],
            ['Confidence Score:', f"{blocker.get('confidence_score', 0):.0%}"]
        ]
        
        details_table = Table(details_data, colWidths=[1.5*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 10))
        
        # Remediation steps
        if blocker.get('detailed_remediation_steps'):
            story.append(Paragraph("Remediation Steps:", self.section_style))
            for step in blocker['detailed_remediation_steps']:
                story.append(Paragraph(f"• {step}", self.bullet_style))
        else:
            story.append(Paragraph("Remediation:", self.section_style))
            story.append(Paragraph(blocker.get('remediation', 'No remediation available'), self.body_style))
        
        # Effort and impact
        if blocker.get('estimated_effort') or blocker.get('business_impact'):
            story.append(Spacer(1, 10))
            
            effort_impact_data = []
            if blocker.get('estimated_effort'):
                effort_impact_data.append(['Estimated Effort:', blocker['estimated_effort']])
            if blocker.get('business_impact'):
                effort_impact_data.append(['Business Impact:', blocker['business_impact']])
            
            if effort_impact_data:
                effort_table = Table(effort_impact_data, colWidths=[1.5*inch, 4*inch])
                effort_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP')
                ]))
                story.append(effort_table)
        
        story.append(Spacer(1, 20))
        
        return story
    
    def _create_recommendations_section(self, session_data: Dict) -> List:
        """Create recommendations and next steps section"""
        
        story = []
        
        story.append(Paragraph("Recommendations and Next Steps", self.subtitle_style))
        
        # General recommendations
        recommendations = [
            "Prioritize critical and high-severity blockers for immediate attention",
            "Develop a phased remediation approach starting with quick wins",
            "Establish a testing environment to validate remediation steps",
            "Create a rollback plan for each remediation activity",
            "Monitor progress and adjust timelines based on actual effort",
            "Consider modernization opportunities during remediation"
        ]
        
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", self.bullet_style))
        
        story.append(Spacer(1, 20))
        
        # Next steps
        story.append(Paragraph("Immediate Next Steps", self.section_style))
        
        next_steps = [
            "Review and validate all identified blockers with technical teams",
            "Prioritize blockers based on business impact and technical complexity",
            "Assign ownership for each blocker remediation",
            "Create detailed project plans for complex remediations",
            "Schedule regular progress reviews and status updates"
        ]
        
        for step in next_steps:
            story.append(Paragraph(f"• {step}", self.bullet_style))
        
        return story
    
    async def _generate_executive_summary(self, session_data: Dict) -> str:
        """Generate AI-powered executive summary"""
        
        blockers = session_data.get('migration_blockers', [])
        total_vms = session_data.get('total_vms', 0)
        
        # Count blockers by severity
        critical_count = len([b for b in blockers if b.get('severity', '').lower() == 'critical'])
        high_count = len([b for b in blockers if b.get('severity', '').lower() == 'high'])
        
        prompt = f"""
        Create an executive summary for a migration blocker analysis report.
        
        CONTEXT:
        - Total VMs to migrate: {total_vms}
        - Total blockers identified: {len(blockers)}
        - Critical blockers: {critical_count}
        - High priority blockers: {high_count}
        
        TOP BLOCKERS SAMPLE:
        {json.dumps(blockers[:5], indent=2)}
        
        Create a 3-4 paragraph executive summary that:
        1. Summarizes the overall migration readiness assessment
        2. Highlights the most critical challenges and their business impact
        3. Provides high-level recommendations and strategic approach
        4. Estimates overall remediation effort, timeline, and success factors
        
        Write in professional, business-focused language suitable for C-level executives.
        Focus on business impact, risk mitigation, and strategic recommendations.
        """
        
        try:
            response = await self.ai_service.invoke_ai(prompt, max_tokens=1000)
            return response if response else self._create_fallback_executive_summary(session_data)
        except Exception as e:
            logger.error(f"Failed to generate AI executive summary: {e}")
            return self._create_fallback_executive_summary(session_data)
    
    async def _generate_remediation_overview(self, session_data: Dict) -> str:
        """Generate AI-powered remediation overview"""
        
        blockers = session_data.get('migration_blockers', [])
        
        prompt = f"""
        Create a remediation planning overview for migration blockers.
        
        BLOCKER DATA:
        {json.dumps(blockers[:10], indent=2)}
        
        Create a comprehensive remediation overview that:
        1. Categorizes blockers by remediation approach (immediate, short-term, long-term)
        2. Identifies common patterns and root causes
        3. Suggests efficient remediation strategies
        4. Recommends resource allocation and team structure
        5. Provides risk mitigation strategies
        
        Focus on practical, actionable guidance for technical teams.
        """
        
        try:
            response = await self.ai_service.invoke_ai(prompt, max_tokens=1200)
            return response if response else self._create_fallback_remediation_overview(session_data)
        except Exception as e:
            logger.error(f"Failed to generate AI remediation overview: {e}")
            return self._create_fallback_remediation_overview(session_data)
    
    def _create_fallback_executive_summary(self, session_data: Dict) -> str:
        """Create fallback executive summary if AI fails"""
        
        blockers = session_data.get('migration_blockers', [])
        total_vms = session_data.get('total_vms', 0)
        critical_count = len([b for b in blockers if b.get('severity', '').lower() == 'critical'])
        
        return f"""
        This migration readiness assessment analyzed {total_vms} virtual machines and identified {len(blockers)} 
        migration blockers that require attention before proceeding with AWS migration.
        
        Of particular concern are {critical_count} critical blockers that pose significant risks to migration 
        success. These issues primarily involve legacy operating systems, complex dependencies, and 
        configuration challenges that must be resolved prior to migration.
        
        We recommend a phased remediation approach, prioritizing critical and high-severity blockers 
        for immediate attention. With proper planning and resource allocation, most blockers can be 
        resolved within 4-8 weeks, enabling a successful migration to AWS.
        
        The detailed analysis and remediation plans in this report provide the technical foundation 
        for migration planning and execution.
        """
    
    def _create_fallback_remediation_overview(self, session_data: Dict) -> str:
        """Create fallback remediation overview if AI fails"""
        
        return """
        The remediation approach should follow a structured methodology focusing on risk mitigation 
        and efficient resource utilization. Critical blockers require immediate attention and should 
        be addressed before proceeding with any migration activities.
        
        High-priority blockers can often be resolved in parallel with migration planning activities, 
        while medium and low-priority issues can be addressed during the migration execution phase.
        
        We recommend establishing dedicated remediation teams with clear ownership and accountability 
        for each blocker category. Regular progress reviews and status updates will ensure timely 
        resolution and successful migration outcomes.
        """
