from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import io
import base64

# Import PDF generation libraries
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Import Google types for artifact handling
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

def generate_order_pdf(order_data: Dict[str, Any], user_id: str = "user123") -> Dict[str, Any]:
    """
    Generate a PDF report for an order containing product details, pricing, and shipping information.
    """
    try:
        if not REPORTLAB_AVAILABLE:
            return {
                "status": "error",
                "error_message": "PDF generation library (reportlab) not available. Please install with: pip install reportlab"
            }

        # Create PDF buffer
        buffer = io.BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1*inch)

        # Container for the 'Flowable' objects
        elements = []

        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )

        # Title
        title = Paragraph("Order Confirmation", title_style)
        elements.append(title)
        elements.append(Spacer(1, 20))

        # Order Information
        order_info = [
            ["Order Number:", order_data.get("order_number", "N/A")],
            ["Order Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Customer ID:", user_id],
            ["Order Status:", order_data.get("status", "Confirmed")]
        ]

        order_table = Table(order_info, colWidths=[2*inch, 3*inch])
        order_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(order_table)
        elements.append(Spacer(1, 20))

        # Order Items
        items_heading = Paragraph("Order Items", heading_style)
        elements.append(items_heading)

        # Create items table
        items_data = [["Product Name", "Price", "Quantity", "Subtotal", "Product URL"]]

        total_cost = 0
        for item in order_data.get("items", []):
            # Extract price value
            price_str = item.get("price", "$0.00").replace("$", "")
            try:
                price_value = float(price_str)
                subtotal = price_value * item.get("quantity", 1)
                total_cost += subtotal
                subtotal_str = f"${subtotal:.2f}"
            except ValueError:
                subtotal_str = "N/A"

            # Truncate URL for display
            url = item.get("url", "N/A")
            display_url = url if len(url) <= 40 else url[:37] + "..."

            items_data.append([
                item.get("name", "Unknown"),
                item.get("price", "N/A"),
                str(item.get("quantity", 1)),
                subtotal_str,
                display_url
            ])

        items_table = Table(items_data, colWidths=[2.5*inch, 1*inch, 0.8*inch, 1*inch, 2*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(items_table)
        elements.append(Spacer(1, 20))

        # Order Total
        total_data = [
            ["Total Items:", str(order_data.get("total_items", 0))],
            ["Total Cost:", f"${total_cost:.2f}"]
        ]

        total_table = Table(total_data, colWidths=[2*inch, 2*inch])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(total_table)
        elements.append(Spacer(1, 20))

        # Shipping Information
        shipping_heading = Paragraph("Shipping Information", heading_style)
        elements.append(shipping_heading)

        shipping_info = [
            ["Shipping Address:", order_data.get("shipping_address", "N/A")],
            ["Payment Method:", order_data.get("payment_method", "N/A")]
        ]

        shipping_table = Table(shipping_info, colWidths=[2*inch, 4*inch])
        shipping_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        elements.append(shipping_table)
        elements.append(Spacer(1, 30))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.grey
        )

        footer_text = """
        <para>
        <b>Thank you for your order!</b><br/>
        This is a demo order confirmation from Cymbal Shops.<br/>
        No real payment has been processed.
        </para>
        """

        footer = Paragraph(footer_text, footer_style)
        elements.append(footer)

        # Build PDF
        doc.build(elements)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Encode to base64 for storage/transmission
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

        return {
            "status": "success",
            "message": f"PDF generated successfully for order {order_data.get('order_number', 'N/A')}",
            "pdf_base64": pdf_base64,
            "pdf_size_bytes": len(pdf_bytes),
            "order_number": order_data.get("order_number", "N/A")
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to generate PDF: {str(e)}",
            "order_data": order_data
        }

async def export_order_to_pdf(order_data: Dict[str, Any], user_id: str = "user123", tool_context: ToolContext = None) -> Dict[str, Any]:
    """
    Export an order to PDF format and save as an artifact.
    """
    try:
        if not GENAI_AVAILABLE:
            return {
                "status": "error",
                "error_message": "Google AI types not available for artifact handling"
            }

        # Generate PDF
        pdf_result = generate_order_pdf(order_data, user_id)

        if pdf_result["status"] != "success":
            return pdf_result

        # Create filename
        order_number = order_data.get("order_number", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"order_{order_number}_{timestamp}.pdf"

        # Convert base64 back to bytes
        pdf_bytes = base64.b64decode(pdf_result["pdf_base64"])

        # Save as artifact if tool_context is available
        if tool_context:
            # Create Part object for PDF
            pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
            await tool_context.save_artifact(filename=filename, artifact=pdf_part)

            return {
                "status": "success",
                "message": f"Order PDF exported successfully as {filename}",
                "filename": filename,
                "order_number": order_number,
                "pdf_size_bytes": len(pdf_bytes)
            }
        else:
            # Return PDF data if no tool context
            return {
                "status": "success",
                "message": "PDF generated successfully",
                "pdf_base64": pdf_result["pdf_base64"],
                "suggested_filename": filename,
                "order_number": order_number,
                "pdf_size_bytes": len(pdf_bytes)
            }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to export order to PDF: {str(e)}",
            "order_data": order_data
        }

def validate_order_data(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that order data contains required fields for PDF generation.
    """
    try:
        required_fields = ["order_number", "items", "shipping_address", "payment_method"]
        missing_fields = []

        for field in required_fields:
            if field not in order_data or not order_data[field]:
                missing_fields.append(field)

        if missing_fields:
            return {
                "status": "error",
                "error_message": f"Missing required fields: {', '.join(missing_fields)}",
                "required_fields": required_fields
            }

        # Validate items structure
        items = order_data.get("items", [])
        if not isinstance(items, list) or len(items) == 0:
            return {
                "status": "error",
                "error_message": "Order must contain at least one item"
            }

        # Check each item has required fields
        for i, item in enumerate(items):
            item_required = ["name", "price", "quantity"]
            for field in item_required:
                if field not in item:
                    return {
                        "status": "error",
                        "error_message": f"Item {i+1} missing required field: {field}"
                    }

        return {
            "status": "success",
            "message": "Order data validation passed"
        }

    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Validation error: {str(e)}"
        }

def get_system_requirements() -> Dict[str, Any]:
    """
    Check system requirements for PDF generation.
    """
    return {
        "reportlab_available": REPORTLAB_AVAILABLE,
        "genai_available": GENAI_AVAILABLE,
        "requirements": {
            "reportlab": "pip install reportlab",
            "google-genai": "pip install google-genai"
        },
        "status": "ready" if REPORTLAB_AVAILABLE and GENAI_AVAILABLE else "missing_dependencies"
    }

def get_order_from_placement_agent(user_id: str = "user123") -> Dict[str, Any]:
    """
    Get the latest order from the order placement agent for export.
    This function imports and calls the order placement agent's get_latest_order function.
    """
    try:
        # Import here to avoid circular imports
        from ..order_placement_agent.agent import get_latest_order

        order_result = get_latest_order(user_id)
        if order_result["status"] == "success":
            return {
                "status": "success",
                "order_data": order_result["order"],
                "message": f"Retrieved order {order_result['order']['order_number']} for export"
            }
        else:
            return {
                "status": "error",
                "error_message": order_result["error_message"]
            }

    except ImportError as e:
        return {
            "status": "error",
            "error_message": "Could not access order placement agent"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Failed to retrieve order: {str(e)}"
        }

# Agent Definition
export_agent = LlmAgent(
    name="export_agent",
    model="gemini-2.0-flash",
    description="Exports order data to PDF format with product details, pricing, and shipping information",
    instruction="""
    You are an export agent that specializes in generating PDF reports for e-commerce orders.

    Your main capabilities:
    1. **export_order_to_pdf** - Exports order data to a formatted PDF document
    2. **generate_order_pdf** - Generates PDF content from order data
    3. **validate_order_data** - Validates order data before PDF generation
    4. **get_system_requirements** - Checks if required libraries are installed
    5. **get_order_from_placement_agent** - Retrieves the latest order from the order placement system

    **PDF Content Includes:**
    - Order confirmation header with order number and date
    - Customer information
    - Detailed product list with names, prices, quantities, and URLs
    - Order totals and cost breakdown
    - Shipping address and payment method information
    - Professional formatting with tables and styling

    **Workflow:**
    1. Use get_order_from_placement_agent to retrieve the latest order data (if no order data provided)
    2. Validate the order data using validate_order_data
    3. Check system requirements if needed with get_system_requirements
    4. Generate and export the PDF using export_order_to_pdf
    5. Provide the user with the generated PDF filename and details

    **Error Handling:**
    - Always validate order data before attempting PDF generation
    - Check for missing required fields (order_number, items, shipping_address, payment_method)
    - Verify that items array contains valid product information
    - Handle missing dependencies gracefully with helpful installation instructions

    **Response Format for Success:**
    "✅ **PDF Export Complete**

    📄 **File:** [filename]
    📋 **Order:** [order_number]
    📊 **Size:** [file_size] bytes

    **Contents:**
    - Order confirmation details
    - [X] products with prices and URLs
    - Shipping and payment information
    - Professional formatting

    💡 The PDF has been saved as an artifact and is ready for download!"

    **Response Format for Errors:**
    "❌ **Export Failed**

    **Error:** [error_message]

    **Suggestion:** [helpful_next_step]

    Would you like me to help resolve this issue?"

    **Important Notes:**
    - Always validate input data before processing
    - Provide clear error messages and solutions
    - Include all required order details in the PDF
    - Use professional formatting for business documents
    - Handle missing dependencies gracefully
    """,
    tools=[export_order_to_pdf, generate_order_pdf, validate_order_data, get_system_requirements, get_order_from_placement_agent],
    output_key="pdf_export"
)