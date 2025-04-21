import io
import datetime
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from services.openai_service import generate_nutrition_plan
from services.firebase_service import upload_pdf_to_firebase
import config

def generate_nutrition_plan_pdf(user_profile, log_message=print):
    """Generate a PDF with the nutrition plan"""
    try:
        # Get the full nutrition plan text
        plan_text = generate_nutrition_plan(user_profile, full_plan=True, log_message=log_message)
        
        # Create an in-memory PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            name='TitleStyle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.darkgreen,
            spaceAfter=12
        )
        
        heading_style = ParagraphStyle(
            name='HeadingStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkgreen,
            spaceBefore=12,
            spaceAfter=6
        )
        
        normal_style = ParagraphStyle(
            name='NormalStyle',
            parent=styles['Normal'],
            fontSize=11,
            leading=14
        )
        
        # Build the PDF content
        elements = []
        
        # Title
        elements.append(Paragraph("FuelQ Pro - Plano Nutricional Personalizado", title_style))
        elements.append(Spacer(1, 12))
        
        # Profile section
        elements.append(Paragraph("Seu Perfil", heading_style))
        
        # Profile data
        profile_data = [[config.LABELS.get(k, k), v] for k, v in user_profile.items()]
        profile_table = Table(profile_data, colWidths=[200, 300])
        profile_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.darkblue),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(profile_table)
        elements.append(Spacer(1, 24))
        
        # Nutrition Plan
        elements.append(Paragraph("Seu Plano Nutricional", heading_style))
        
        # Convert plan text to paragraphs
        for line in plan_text.split('\n'):
            if line.strip():
                if line.startswith('🔹'):
                    elements.append(Paragraph(line, heading_style))
                else:
                    elements.append(Paragraph(line, normal_style))
                    elements.append(Spacer(1, 4))
        
        # Disclaimer
        elements.append(Spacer(1, 24))
        elements.append(Paragraph(
            "Este plano é uma recomendação geral. Para orientações específicas, consulte um nutricionista.", 
            ParagraphStyle(name='Disclaimer', parent=styles['Italic'], textColor=colors.grey)
        ))
        
        # Build the PDF
        doc.build(elements)
        
        # Get the PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Upload the PDF to Firebase and get URL
        pdf_url = None
        if pdf_bytes:
            pdf_url = upload_pdf_to_firebase(pdf_bytes, user_profile, log_message)
        
        return pdf_bytes, pdf_url
        
    except Exception as e:
        log_message(f">>> ERROR generating PDF: {str(e)}")
        return None,