def calculate_confidence_scores(extracted_data, ocr_results):
    """Calculate confidence scores for extracted data"""
    confidence = {}
    
    # Default confidence level
    default_confidence = 0.5
    
    # Get combined OCR text
    if isinstance(ocr_results, dict) and 'full_text' in ocr_results:
        ocr_text = ocr_results['full_text']
    elif isinstance(ocr_results, dict) and 'combined_text' in ocr_results:
        ocr_text = ocr_results['combined_text']
    elif isinstance(ocr_results, dict) and 'text' in ocr_results:
        ocr_text = ocr_results['text']
    else:
        ocr_text = ""
    
    # Vendor confidence
    vendor = extracted_data.get('vendor')
    if vendor:
        # Check if vendor appears in OCR text
        if vendor.lower() in ocr_text.lower():
            # Higher confidence if it appears at the beginning
            if ocr_text.lower().startswith(vendor.lower()):
                confidence['vendor'] = 0.9
            else:
                confidence['vendor'] = 0.7
        else:
            confidence['vendor'] = 0.3
    else:
        confidence['vendor'] = 0.0
    
    # Date confidence
    date = extracted_data.get('date')
    if date:
        # Check if date is in a standard format
        if len(date) == 10 and date[4] == '-' and date[7] == '-':
            confidence['date'] = 0.8
        else:
            confidence['date'] = 0.5
    else:
        confidence['date'] = 0.0
    
    # Total confidence
    total = extracted_data.get('total')
    if total is not None:
        # Check if total appears in validation flags
        if 'validation_flags' in extracted_data and 'total_mismatch' in extracted_data['validation_flags']:
            mismatch = extracted_data['validation_flags']['total_mismatch']
            difference_ratio = abs(mismatch['difference']) / max(mismatch['extracted_total'], 0.01)
            
            # Lower confidence if there's a significant mismatch
            if difference_ratio > 0.1:  # More than 10% difference
                confidence['total'] = 0.3
            else:
                confidence['total'] = 0.6
        else:
            confidence['total'] = 0.8
    else:
        confidence['total'] = 0.0
    
    # Invoice number confidence
    invoice_number = extracted_data.get('invoice_number')
    if invoice_number:
        # Check if it has a typical format (alphanumeric)
        if any(c.isalpha() for c in invoice_number) and any(c.isdigit() for c in invoice_number):
            confidence['invoice_number'] = 0.8
        else:
            confidence['invoice_number'] = 0.5
    else:
        confidence['invoice_number'] = 0.0
    
    # Tax amount confidence
    tax_amount = extracted_data.get('tax_amount')
    if tax_amount is not None:
        # Check if tax amount is reasonable (typically 5-15% of total)
        if total is not None and total > 0:
            tax_ratio = tax_amount / total
            if 0.01 <= tax_ratio <= 0.15:  # Reasonable tax range
                confidence['tax_amount'] = 0.8
            else:
                confidence['tax_amount'] = 0.4
        else:
            confidence['tax_amount'] = 0.5
    else:
        confidence['tax_amount'] = 0.0
    
    # Shipping cost confidence
    shipping_cost = extracted_data.get('shipping_cost')
    if shipping_cost is not None:
        confidence['shipping_cost'] = 0.7
    else:
        confidence['shipping_cost'] = 0.0
    
    # Platform fee confidence
    platform_fee = extracted_data.get('platform_fee')
    if platform_fee is not None:
        confidence['platform_fee'] = 0.7
    else:
        confidence['platform_fee'] = 0.0
    
    # Platform name confidence
    platform_name = extracted_data.get('platform_name')
    if platform_name:
        # Check if platform name appears in OCR text
        if platform_name.lower() in ocr_text.lower():
            confidence['platform_name'] = 0.8
        else:
            confidence['platform_name'] = 0.4
    else:
        confidence['platform_name'] = 0.0
    
    # Items confidence
    items = extracted_data.get('items', [])
    if items:
        item_confidences = []
        for item in items:
            item_conf = {}
            
            # Name confidence
            name = item.get('name', '')
            if name and len(name) > 3:
                item_conf['name'] = 0.7
            else:
                item_conf['name'] = 0.3
            
            # Price confidence
            price = item.get('price', 0)
            if price > 0:
                item_conf['price'] = 0.8
            else:
                item_conf['price'] = 0.2
            
            # Quantity confidence
            quantity = item.get('quantity', 0)
            if quantity > 0:
                item_conf['quantity'] = 0.9
            else:
                item_conf['quantity'] = 0.3
            
            # SKU confidence
            sku = item.get('sku')
            if sku:
                item_conf['sku'] = 0.7
            else:
                item_conf['sku'] = 0.0
            
            # Condition confidence
            condition = item.get('condition')
            if condition:
                item_conf['condition'] = 0.6
            else:
                item_conf['condition'] = 0.0
            
            # Overall item confidence
            item_conf['overall'] = (
                item_conf.get('name', 0) * 0.5 + 
                item_conf.get('price', 0) * 0.3 + 
                item_conf.get('quantity', 0) * 0.2
            )
            
            item_confidences.append(item_conf)
        
        # Average confidence across all items
        if item_confidences:
            confidence['items'] = sum(item.get('overall', 0) for item in item_confidences) / len(item_confidences)
        else:
            confidence['items'] = 0.0
    else:
        confidence['items'] = 0.0
    
    # Overall confidence
    weights = {
        'vendor': 0.15,
        'date': 0.1,
        'total': 0.2,
        'invoice_number': 0.05,
        'items': 0.5
    }
    
    weighted_sum = sum(confidence.get(field, 0) * weight for field, weight in weights.items())
    total_weight = sum(weight for field, weight in weights.items() if field in confidence)
    
    if total_weight > 0:
        confidence['overall'] = weighted_sum / total_weight
    else:
        confidence['overall'] = 0.0
    
    return confidence
