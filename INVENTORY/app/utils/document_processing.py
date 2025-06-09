import os
import logging
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import re
import PyPDF2
from bs4 import BeautifulSoup

from app.utils.image_preprocessing import apply_best_preprocessing
from app.utils.ocr_engines import perform_multi_engine_ocr, try_multiple_preprocessed_versions
from app.utils.ollama_vision import OllamaVision
from app.utils.validation_rules import validate_extracted_data, detect_condition, extract_sku
from app.utils.confidence_scoring import calculate_confidence_scores

# Initialize Ollama Vision client
ollama_vision = OllamaVision(model_name="llama3.2-vision:11b")

def save_uploaded_file(file, upload_folder):
    """Save an uploaded file and return the path"""
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{timestamp}_{filename}"
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    return file_path

def detect_file_type(file_path):
    """Detect the type of document"""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
        return 'image'
    elif file_ext == '.pdf':
        return 'pdf'
    elif file_ext in ['.html', '.htm', '.xml']:
        return 'markup'
    elif file_ext in ['.csv', '.xlsx', '.xls']:
        return 'spreadsheet'
    else:
        return 'unknown'

def extract_data_from_ocr(text, text_elements):
    """Extract structured data from OCR text"""
    import re
    
    # Initialize extracted data
    extracted_data = {
        'vendor': None,
        'date': None,
        'total': None,
        'invoice_number': None,
        'tax_amount': None,
        'shipping_cost': None,
        'platform_fee': None,
        'other_fees': None,
        'platform_name': None,
        'platform_url': None,
        'items': []
    }
    
    # Extract vendor (usually at the top of receipt)
    lines = text.split('\n')
    if lines and lines[0].strip():
        extracted_data['vendor'] = lines[0].strip()
    
    # Extract date
    date_patterns = [
        r'\b(?:date|dated|invoice date|receipt date|order date)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'\b(?:date|dated|invoice date|receipt date|order date)[\s:]*(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b'
    ]
    
    for pattern in date_patterns:
        date_match = re.search(pattern, text, re.IGNORECASE)
        if date_match:
            extracted_data['date'] = date_match.group(1)
            break
    
    # Extract invoice/receipt/order number
    invoice_patterns = [
        r'(?:invoice|receipt|order)[\s#:]*(\w+[-\w]*)',
        r'(?:invoice|receipt|order)[\s#:]*#\s*(\w+[-\w]*)',
        r'#\s*(\w+[-\w]*)',
        r'(?:invoice|receipt|order) (?:number|no|num|#)[\s:]*(\w+[-\w]*)',
        r'(?:invoice|receipt|order) (?:number|no|num|#)[\s:]*#\s*(\w+[-\w]*)'
    ]
    
    for pattern in invoice_patterns:
        invoice_match = re.search(pattern, text, re.IGNORECASE)
        if invoice_match:
            extracted_data['invoice_number'] = invoice_match.group(1)
            break
    
    # Extract platform name (for sales platforms like eBay, Amazon, etc.)
    platform_patterns = [
        r'\b(ebay|amazon|etsy|mercari|poshmark|depop|offerup|facebook marketplace|craigslist)\b'
    ]
    
    for pattern in platform_patterns:
        platform_match = re.search(pattern, text, re.IGNORECASE)
        if platform_match:
            extracted_data['platform_name'] = platform_match.group(1).title()
            break
    
    # Extract platform URL
    url_patterns = [
        r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)(?:/\S*)?'
    ]
    
    for pattern in url_patterns:
        url_match = re.search(pattern, text)
        if url_match:
            extracted_data['platform_url'] = url_match.group(0)
            # If we found a URL but no platform name, try to extract from domain
            if not extracted_data['platform_name']:
                domain = url_match.group(1).lower()
                if 'ebay' in domain:
                    extracted_data['platform_name'] = 'eBay'
                elif 'amazon' in domain:
                    extracted_data['platform_name'] = 'Amazon'
                elif 'etsy' in domain:
                    extracted_data['platform_name'] = 'Etsy'
                # Add more platforms as needed
            break
    
    # Extract total amount
    total_patterns = [
        r'(?:total|amount|sum|grand total)[\s:]*\$?\s*([\d,]+\.\d{2})',
        r'(?:total|amount|sum|grand total)[\s:]*\$?\s*([\d,]+)',
        r'(?:total|amount|sum|grand total)[\s:]*\$\s*([\d,]+\.\d{2})',
        r'(?:total|amount|sum|grand total)[\s:]*\$\s*([\d,]+)'
    ]
    
    for pattern in total_patterns:
        total_match = re.search(pattern, text, re.IGNORECASE)
        if total_match:
            extracted_data['total'] = float(total_match.group(1).replace(',', ''))
            break
    
    # Extract tax amount
    tax_patterns = [
        r'(?:tax|sales tax|vat|gst)[\s:]*\$?\s*([\d,]+\.\d{2})',
        r'(?:tax|sales tax|vat|gst)[\s:]*\$?\s*([\d,]+)',
        r'(?:tax|sales tax|vat|gst)[\s:]*\$\s*([\d,]+\.\d{2})',
        r'(?:tax|sales tax|vat|gst)[\s:]*\$\s*([\d,]+)'
    ]
    
    for pattern in tax_patterns:
        tax_match = re.search(pattern, text, re.IGNORECASE)
        if tax_match:
            extracted_data['tax_amount'] = float(tax_match.group(1).replace(',', ''))
            break
    
    # Extract shipping cost
    shipping_patterns = [
        r'(?:shipping|delivery|postage|freight)[\s:]*\$?\s*([\d,]+\.\d{2})',
        r'(?:shipping|delivery|postage|freight)[\s:]*\$?\s*([\d,]+)',
        r'(?:shipping|delivery|postage|freight)[\s:]*\$\s*([\d,]+\.\d{2})',
        r'(?:shipping|delivery|postage|freight)[\s:]*\$\s*([\d,]+)'
    ]
    
    for pattern in shipping_patterns:
        shipping_match = re.search(pattern, text, re.IGNORECASE)
        if shipping_match:
            extracted_data['shipping_cost'] = float(shipping_match.group(1).replace(',', ''))
            break
    
    # Extract platform fees
    fee_patterns = [
        r'(?:fee|commission|platform fee|service fee)[\s:]*\$?\s*([\d,]+\.\d{2})',
        r'(?:fee|commission|platform fee|service fee)[\s:]*\$?\s*([\d,]+)',
        r'(?:fee|commission|platform fee|service fee)[\s:]*\$\s*([\d,]+\.\d{2})',
        r'(?:fee|commission|platform fee|service fee)[\s:]*\$\s*([\d,]+)'
    ]
    
    for pattern in fee_patterns:
        fee_match = re.search(pattern, text, re.IGNORECASE)
        if fee_match:
            extracted_data['platform_fee'] = float(fee_match.group(1).replace(',', ''))
            break
    
    # Extract items (this is complex and depends on receipt format)
    # Try multiple approaches for better accuracy
    
    # First, split text into lines for line-by-line analysis
    lines = text.split('\n')
    
    # Approach 1: Look for quantity-item-price patterns (common in receipts)
    item_pattern1 = r'(\d+)\s+([A-Za-z0-9][\w\s\-&\'".]+?)\s+\$?\s*([\d,]+\.\d{2})'
    item_matches1 = []
    
    # Try to find matches in each line
    for line in lines:
        matches = re.finditer(item_pattern1, line)
        for match in matches:
            quantity, name, price = match.groups()
            item_matches1.append({
                'quantity': int(quantity),
                'name': name.strip(),
                'price': float(price.replace(',', '')),
                'condition': detect_condition(name),
                'sku': extract_sku(name, text),
                'line': line
            })
    
    # Approach 2: Look for item-price patterns (assume quantity=1)
    item_pattern2 = r'([A-Za-z0-9][\w\s\-&\'".]+?)\s+\$?\s*([\d,]+\.\d{2})'
    item_matches2 = []
    
    # Try to find matches in each line
    for line in lines:
        # Skip if it looks like a total/subtotal/tax line
        if re.search(r'total|tax|shipping|fee|discount|subtotal', line, re.IGNORECASE):
            continue
            
        matches = re.finditer(item_pattern2, line)
        for match in matches:
            name, price = match.groups()
            item_matches2.append({
                'quantity': 1,
                'name': name.strip(),
                'price': float(price.replace(',', '')),
                'condition': detect_condition(name),
                'sku': extract_sku(name, text),
                'line': line
            })
    
    # Approach 3: Look for lines with just a price and use previous line as item name
    item_pattern3 = []
    for i, line in enumerate(lines):
        if i == 0:
            continue  # Skip first line
            
        # Look for lines with just a price
        price_match = re.search(r'^\s*\$?\s*([\d,]+\.\d{2})\s*$', line)
        if price_match and i > 0:
            price = float(price_match.group(1).replace(',', ''))
            # Use previous line as item name if it doesn't contain a price
            prev_line = lines[i-1]
            if not re.search(r'\$\s*[\d,]+\.\d{2}', prev_line):
                item_pattern3.append({
                    'quantity': 1,
                    'name': prev_line.strip(),
                    'price': price,
                    'condition': detect_condition(prev_line),
                    'sku': extract_sku(prev_line, text),
                    'line': line
                })
    
    # Choose the approach that found more items
    approaches = [item_matches1, item_matches2, item_pattern3]
    best_approach = max(approaches, key=len)
    
    # Filter out likely false positives
    filtered_items = []
    for item in best_approach:
        # Skip items with very short names (likely errors)
        if len(item['name']) < 3:
            continue
            
        # Skip items with very high prices (likely errors or totals)
        if item['price'] > 10000:
            continue
            
        # Skip items with common keywords that indicate they're not actual items
        if re.search(r'\b(total|subtotal|tax|shipping|fee|discount|payment|credit|card|cash)\b', 
                    item['name'], re.IGNORECASE):
            continue
            
        # Add to filtered items
        filtered_items.append({
            'quantity': item['quantity'],
            'name': item['name'],
            'price': item['price'],
            'condition': item['condition'],
            'sku': item['sku']
        })
    
    extracted_data['items'] = filtered_items
    
    # If no items were found, try a more aggressive approach
    if not extracted_data['items']:
        # Look for any price-like patterns and associate with nearby text
        price_pattern = r'\$\s*([\d,]+\.\d{2})'
        
        for line in lines:
            price_match = re.search(price_pattern, line)
            if not price_match:
                continue
                
            price = float(price_match.group(1).replace(',', ''))
            
            # Skip if this looks like a total/subtotal/tax amount
            if (extracted_data['total'] == price or 
                extracted_data['tax_amount'] == price or 
                extracted_data['shipping_cost'] == price or 
                extracted_data['platform_fee'] == price):
                continue
            
            # Extract potential item name from the line (everything before the price)
            start_pos = line.find('$')
            if start_pos > 3:  # Ensure there's enough text before the price
                name = line[:start_pos].strip()
                # Skip if name contains keywords that indicate it's not an item
                if not re.search(r'\b(total|subtotal|tax|shipping|fee|discount|payment|credit|card|cash)\b', 
                               name, re.IGNORECASE):
                    extracted_data['items'].append({
                        'quantity': 1,
                        'name': name,
                        'price': price,
                        'condition': detect_condition(name),
                        'sku': extract_sku(name, text)
                    })
    
    return extracted_data

def combine_ocr_and_vision_results(ocr_data, vision_data):
    """Combine results from OCR and Vision LLM for better accuracy
    
    Args:
        ocr_data (dict): Data extracted using OCR
        vision_data (dict): Data extracted using Vision LLM
        
    Returns:
        dict: Combined data with the best values from both sources
    """
    # Start with OCR data as base
    combined_data = ocr_data.copy()
    
    # For each field, use Vision LLM data if OCR data is missing or has low confidence
    # Vendor name
    if not combined_data.get('vendor') and vision_data.get('vendor'):
        combined_data['vendor'] = vision_data.get('vendor')
        
    # Date
    if not combined_data.get('date') and vision_data.get('date'):
        combined_data['date'] = vision_data.get('date')
        
    # Invoice number
    if not combined_data.get('invoice_number') and vision_data.get('invoice_number'):
        combined_data['invoice_number'] = vision_data.get('invoice_number')
        
    # Total amount
    if not combined_data.get('total') and vision_data.get('total'):
        combined_data['total'] = vision_data.get('total')
        
    # Tax amount
    if not combined_data.get('tax_amount') and vision_data.get('tax_amount'):
        combined_data['tax_amount'] = vision_data.get('tax_amount')
        
    # Shipping cost
    if not combined_data.get('shipping_cost') and vision_data.get('shipping_cost'):
        combined_data['shipping_cost'] = vision_data.get('shipping_cost')
    
    # Items - merge items from both sources, removing duplicates
    ocr_items = combined_data.get('items', [])
    vision_items = vision_data.get('items', [])
    
    # If OCR found no items but Vision LLM did, use Vision LLM items
    if not ocr_items and vision_items:
        combined_data['items'] = vision_items
    # If both found items, merge them intelligently
    elif ocr_items and vision_items:
        # Create a set of item names from OCR to check for duplicates
        ocr_item_names = {item.get('name', '').lower() for item in ocr_items}
        
        # Add Vision LLM items that aren't duplicates
        for vision_item in vision_items:
            vision_item_name = vision_item.get('name', '').lower()
            # Check if this item is already in OCR items
            if vision_item_name and vision_item_name not in ocr_item_names:
                # Add condition and SKU if missing
                if 'condition' not in vision_item or not vision_item['condition']:
                    vision_item['condition'] = detect_condition(vision_item.get('name', ''))
                if 'sku' not in vision_item or not vision_item['sku']:
                    vision_item['sku'] = extract_sku(vision_item.get('name', ''), '')
                
                # Add to combined items
                combined_data['items'].append(vision_item)
    
    return combined_data

def process_image_document(image_path):
    """Process an image document with enhanced OCR accuracy and Vision LLM"""
    try:
        # First, classify the receipt to determine the best processing approach
        from app.utils.receipt_classifier import classify_receipt
        classification = classify_receipt(image_path)
        receipt_type = classification.get('receipt_type', 'unknown')
        source_type = classification.get('source_type', 'unknown')
        
        logging.info(f"Receipt classified as: {receipt_type}, source type: {source_type}")
        
        # Apply type-specific preprocessing techniques
        preprocessed_images = apply_best_preprocessing(image_path)
        
        # Try OCR on multiple preprocessed versions to find the best result
        ocr_result = try_multiple_preprocessed_versions(preprocessed_images)
        
        # Extract text from OCR result
        if 'error' in ocr_result:
            logging.error(f"OCR failed on all image versions: {ocr_result['error']}")
            return {'error': f"OCR failed on all image versions: {ocr_result['error']}"}
        
        # Get text and text elements
        combined_text = ocr_result.get('full_text', '')
        text_elements = ocr_result.get('text_elements', [])
        
        # Log which preprocessing version worked best
        preprocessing_version = ocr_result.get('preprocessing_version', 'unknown')
        logging.info(f"Best OCR result from preprocessing version: {preprocessing_version}")
        
        # Extract structured data from OCR results
        ocr_extracted_data = extract_data_from_ocr(combined_text, text_elements)
        
        # Process with Ollama Vision LLM (which now uses receipt type-specific prompts)
        logging.info(f"Processing {receipt_type} receipt with Ollama Vision LLM: {image_path}")
        vision_result = ollama_vision.analyze_receipt(image_path)
        
        # Check if Vision LLM was successful
        if 'error' in vision_result:
            logging.warning(f"Vision LLM analysis failed: {vision_result.get('error')}")
            vision_extracted_data = {}
        else:
            vision_extracted_data = vision_result
            logging.info("Vision LLM analysis successful")
        
        # Combine results from OCR and Vision LLM
        if vision_extracted_data:
            combined_extracted_data = combine_ocr_and_vision_results(ocr_extracted_data, vision_extracted_data)
            logging.info("Combined OCR and Vision LLM results")
        else:
            combined_extracted_data = ocr_extracted_data
            logging.info("Using OCR results only (Vision LLM failed)")
        
        # Make a second LLM call to refine and clean up the results
        logging.info("Making second LLM call to refine and clean up results")
        refined_data = ollama_vision.refine_extracted_data(combined_extracted_data, combined_text)
        
        if refined_data:
            logging.info("Successfully refined the extracted data")
            # Check if refinement improved the data
            if len(refined_data.get('items', [])) > 0:
                combined_extracted_data = refined_data
            else:
                logging.warning("Refinement removed all items, using original combined data")
        else:
            logging.warning("Refinement failed, using original combined data")
        
        # Validate the combined and refined data
        validated_data = validate_extracted_data(combined_extracted_data)
        
        # Calculate confidence scores
        confidence_scores = calculate_confidence_scores(validated_data, {'combined_text': combined_text})
        
        # Force garbage collection
        import gc
        gc.collect()
        
        return {
            'extracted_data': validated_data,
            'confidence_scores': confidence_scores,
            'ocr_results': {
                'combined_text': combined_text
            },
            'vision_results': vision_extracted_data if vision_extracted_data else None,
            'preprocessed_images': preprocessed_images,
            'receipt_classification': classification  # Include the receipt classification in the results
        }
    except Exception as e:
        logging.error(f"Error in image document processing: {str(e)}")
        return {'error': str(e)}

def process_pdf_document(pdf_path):
    """Process a PDF document using PyPDF2"""
    # Extract text directly from PDF
    extracted_text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text() or ""
                extracted_text += page_text + "\n"
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {str(e)}")
        return {'error': f"Failed to extract text from PDF: {str(e)}"}
    
    # If extraction yielded text, process it
    if extracted_text.strip():
        # Extract structured data from text
        extracted_data = extract_data_from_ocr(extracted_text, [])
        
        # Validate the extracted data
        validated_data = validate_extracted_data(extracted_data)
        
        # Calculate confidence scores
        confidence_scores = calculate_confidence_scores(validated_data, {'text': extracted_text})
        
        # Force garbage collection
        import gc
        gc.collect()
        
        return {
            'extracted_data': validated_data,
            'confidence_scores': confidence_scores,
            'text_extraction': extracted_text,
            'extraction_method': 'direct_pdf'
        }
    else:
        return {'error': 'No text could be extracted from the PDF'}

def process_markup_document(markup_path):
    """Process HTML/XML document (e.g., eBay invoice)"""
    try:
        with open(markup_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the HTML/XML
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract text
        text = soup.get_text(separator=' ', strip=True)
        
        # Extract structured data from text
        extracted_data = extract_data_from_ocr(text, [])
        
        # For eBay invoices, look for specific elements
        if not extracted_data['platform_name']:
            extracted_data['platform_name'] = 'eBay'  # Default for eBay invoices
        
        # Try to find order/invoice number
        invoice_elem = soup.find(string=lambda text: 'order' in str(text).lower() and '#' in str(text))
        if invoice_elem:
            invoice_match = re.search(r'#\s*(\w+)', str(invoice_elem))
            if invoice_match:
                extracted_data['invoice_number'] = invoice_match.group(1)
        
        # Validate the extracted data
        validated_data = validate_extracted_data(extracted_data)
        
        # Calculate confidence scores
        confidence_scores = calculate_confidence_scores(validated_data, {'text': text})
        
        return {
            'extracted_data': validated_data,
            'confidence_scores': confidence_scores,
            'text_extraction': text,
            'extraction_method': 'markup_parsing'
        }
    
    except Exception as e:
        logging.error(f"Error processing markup document: {str(e)}")
        return {'error': str(e)}

def process_document(file_path):
    """Process a document based on its type"""
    # Detect file type
    file_type = detect_file_type(file_path)
    
    # Process based on file type
    if file_type == 'image':
        return process_image_document(file_path)
    elif file_type == 'pdf':
        return process_pdf_document(file_path)
    elif file_type == 'markup':
        return process_markup_document(file_path)
    else:
        return {'error': f'Unsupported file type: {file_type}'}

def map_to_inventory_system(extracted_data):
    """Map extracted data to inventory system models"""
    mapped_data = {
        'vendor_info': {
            'name': extracted_data.get('vendor'),
            'platform': extracted_data.get('platform_name'),
            'platform_url': extracted_data.get('platform_url')
        },
        'transaction_info': {
            'invoice_number': extracted_data.get('invoice_number'),
            'date': extracted_data.get('date'),
            'total': extracted_data.get('total'),
            'tax_amount': extracted_data.get('tax_amount'),
            'shipping_cost': extracted_data.get('shipping_cost'),
            'platform_fee': extracted_data.get('platform_fee'),
            'other_fees': extracted_data.get('other_fees')
        },
        'items': []
    }
    
    # Map each extracted item to inventory system format
    for item in extracted_data.get('items', []):
        mapped_item = {
            'name': item.get('name'),
            'sku': item.get('sku'),
            'condition': item.get('condition'),
            'cost_price': item.get('price'),
            'quantity': item.get('quantity', 1),
            'location': f"Receipt import: {extracted_data.get('date') or datetime.now().strftime('%Y-%m-%d')}"
        }
        mapped_data['items'].append(mapped_item)
    
    return mapped_data
