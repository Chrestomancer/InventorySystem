import re
from datetime import datetime
import logging

def validate_date(date_str):
    """Validate and normalize date format"""
    if not date_str:
        return None
    
    # Common date formats
    date_formats = [
        '%Y-%m-%d',      # 2025-03-03
        '%m/%d/%Y',      # 03/03/2025
        '%d/%m/%Y',      # 03/03/2025 (day first)
        '%m-%d-%Y',      # 03-03-2025
        '%d-%m-%Y',      # 03-03-2025 (day first)
        '%B %d, %Y',     # March 3, 2025
        '%d %B %Y',      # 3 March 2025
        '%b %d, %Y',     # Mar 3, 2025
        '%d %b %Y',      # 3 Mar 2025
        '%m.%d.%Y',      # 03.03.2025
        '%d.%m.%Y'       # 03.03.2025 (day first)
    ]
    
    # Try each format
    for fmt in date_formats:
        try:
            date_obj = datetime.strptime(date_str, fmt)
            # Return in standard format
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # If no format matched, try to extract date using regex
    date_patterns = [
        r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})'   # MM/DD/YYYY or DD/MM/YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_str)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                # Determine format based on first group
                if len(groups[0]) == 4:  # YYYY-MM-DD
                    year, month, day = groups
                else:  # MM/DD/YYYY or DD/MM/YYYY
                    # Assume MM/DD/YYYY for simplicity
                    month, day, year = groups
                
                try:
                    # Validate and create date object
                    date_obj = datetime(int(year), int(month), int(day))
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    # If MM/DD/YYYY fails, try DD/MM/YYYY
                    try:
                        date_obj = datetime(int(year), int(day), int(month))
                        return date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
    
    # If all else fails, return the original string
    return date_str

def validate_total(total_value):
    """Validate and normalize total amount"""
    if total_value is None:
        return None
    
    # If it's already a float, return it
    if isinstance(total_value, float):
        return total_value
    
    # If it's a string, try to convert to float
    if isinstance(total_value, str):
        # Remove currency symbols and commas
        cleaned = total_value.replace('$', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            # Try to extract number using regex
            match = re.search(r'(\d+\.\d{2})', cleaned)
            if match:
                return float(match.group(1))
    
    return None

def validate_items(items):
    """Validate and normalize item list"""
    if not items:
        return []
    
    validated_items = []
    
    for item in items:
        # Ensure required fields
        name = item.get('name', '').strip()
        if not name:
            continue  # Skip items without a name
        
        # Normalize quantity
        quantity = item.get('quantity', 1)
        if isinstance(quantity, str):
            try:
                quantity = int(quantity)
            except ValueError:
                quantity = 1
        
        # Normalize price
        price = item.get('price', 0)
        if isinstance(price, str):
            try:
                price = float(price.replace('$', '').replace(',', ''))
            except ValueError:
                price = 0
        
        validated_items.append({
            'name': name,
            'quantity': quantity,
            'price': price,
            'sku': item.get('sku'),
            'condition': item.get('condition')
        })
    
    return validated_items

def detect_condition(item_name):
    """Detect item condition from name"""
    if not item_name:
        return None
        
    condition_keywords = {
        'new': ['new', 'sealed', 'unopened', 'brand new', 'mint'],
        'used': ['used', 'pre-owned', 'preowned', 'pre owned', 'opened', 'played'],
        'refurbished': ['refurbished', 'refurb', 'renewed', 'reconditioned'],
        'damaged': ['damaged', 'broken', 'cracked', 'scratched', 'dented']
    }
    
    item_name_lower = item_name.lower()
    
    for condition, keywords in condition_keywords.items():
        for keyword in keywords:
            if keyword in item_name_lower:
                return condition
    
    return None  # Unknown condition

def extract_sku(item_name, full_text):
    """Try to extract SKU from item name or surrounding text"""
    # Look for common SKU patterns
    sku_patterns = [
        r'SKU[\s:]*([A-Za-z0-9\-]+)',
        r'Item[\s#:]*([A-Za-z0-9\-]+)',
        r'Product[\s#:]*([A-Za-z0-9\-]+)',
        r'Model[\s#:]*([A-Za-z0-9\-]+)',
        r'UPC[\s:]*(\d+)',
        r'EAN[\s:]*(\d+)'
    ]
    
    # First check item name
    for pattern in sku_patterns:
        sku_match = re.search(pattern, item_name, re.IGNORECASE)
        if sku_match:
            return sku_match.group(1)
    
    # Then check full text
    for pattern in sku_patterns:
        sku_match = re.search(pattern, full_text, re.IGNORECASE)
        if sku_match:
            return sku_match.group(1)
    
    return None  # No SKU found

def validate_extracted_data(data):
    """Apply validation rules to extracted data"""
    validated_data = {}
    
    # Validate vendor
    validated_data['vendor'] = data.get('vendor', '').strip() if data.get('vendor') else None
    
    # Validate date
    validated_data['date'] = validate_date(data.get('date'))
    
    # Validate total
    validated_data['total'] = validate_total(data.get('total'))
    
    # Validate invoice number
    validated_data['invoice_number'] = data.get('invoice_number', '').strip() if data.get('invoice_number') else None
    
    # Validate tax amount
    validated_data['tax_amount'] = validate_total(data.get('tax_amount'))
    
    # Validate shipping cost
    validated_data['shipping_cost'] = validate_total(data.get('shipping_cost'))
    
    # Validate platform fee
    validated_data['platform_fee'] = validate_total(data.get('platform_fee'))
    
    # Validate other fees
    validated_data['other_fees'] = validate_total(data.get('other_fees'))
    
    # Validate platform name
    validated_data['platform_name'] = data.get('platform_name', '').strip() if data.get('platform_name') else None
    
    # Validate platform URL
    validated_data['platform_url'] = data.get('platform_url', '').strip() if data.get('platform_url') else None
    
    # Validate items
    validated_data['items'] = validate_items(data.get('items', []))
    
    # Add validation flags
    validated_data['validation_flags'] = {}
    
    # Check if total matches sum of items
    if validated_data['total'] and validated_data['items']:
        items_total = sum(item['price'] * item['quantity'] for item in validated_data['items'])
        if abs(validated_data['total'] - items_total) > 0.01:
            validated_data['validation_flags']['total_mismatch'] = {
                'extracted_total': validated_data['total'],
                'calculated_total': items_total,
                'difference': validated_data['total'] - items_total
            }
    
    # Check if date is in the future
    if validated_data['date']:
        try:
            date_obj = datetime.strptime(validated_data['date'], '%Y-%m-%d')
            if date_obj > datetime.now():
                validated_data['validation_flags']['future_date'] = True
        except ValueError:
            pass
    
    return validated_data
