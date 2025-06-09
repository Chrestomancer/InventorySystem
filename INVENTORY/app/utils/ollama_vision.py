import os
import logging
import json
import ollama
import re
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaVision:
    """Class for interacting with Ollama's vision-capable models"""
    
    def __init__(self, model_name="gemma3", host=None):
        """Initialize the Ollama Vision client
        
        Args:
            model_name (str): Name of the vision-capable model to use
            host (str, optional): Ollama API host URL
        """
        self.model_name = model_name
        self.host = host
        
        # Check if model is available
        self._check_model()
    
    def _check_model(self):
        """Check if the specified model is available in Ollama"""
        try:
            # Use the direct ollama.list() function as shown in the documentation
            models = ollama.list()
            available_models = [model["name"] for model in models.get("models", [])]
            
            if self.model_name not in available_models:
                logger.warning(f"Model '{self.model_name}' not found in Ollama. Available models: {available_models}")
                logger.info(f"You may need to run: ollama pull {self.model_name}")
            else:
                logger.info(f"Using Ollama model: {self.model_name}")
        except Exception as e:
            logger.error(f"Error checking Ollama model: {str(e)}")
    
    def _extract_json_from_text(self, text):
        """Extract valid JSON from text using multiple methods
        
        Args:
            text (str): Text that may contain JSON
            
        Returns:
            dict: Extracted JSON data or None if no valid JSON found
        """
        # Method 1: Simple JSON extraction (find first { and last })
        try:
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            logger.debug("Simple JSON extraction failed, trying advanced methods")
        
        # Method 2: Use regex to find the most complete JSON object
        try:
            # Find all potential JSON objects (starting with { and ending with })
            json_pattern = r'(\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\})'
            matches = re.findall(json_pattern, text)
            
            if matches:
                # Try each match until we find valid JSON
                for match in matches:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            logger.debug("Regex JSON extraction failed, trying line-by-line method")
        
        # Method 3: Try to find JSON line by line (for multi-line JSON with potential errors)
        try:
            lines = text.split('\n')
            json_lines = []
            in_json = False
            brace_count = 0
            
            for line in lines:
                if '{' in line and not in_json:
                    in_json = True
                    brace_count = line.count('{') - line.count('}')
                    json_lines.append(line)
                elif in_json:
                    json_lines.append(line)
                    brace_count += line.count('{') - line.count('}')
                    if brace_count == 0:
                        # We've found a complete JSON object
                        json_str = '\n'.join(json_lines)
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            # Reset and continue looking
                            in_json = False
                            json_lines = []
        except Exception:
            logger.debug("Line-by-line JSON extraction failed")
        
        # Method 4: Try to fix common JSON errors
        try:
            # Find the most promising JSON-like content
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                
                # Fix common JSON errors
                # 1. Fix trailing commas in arrays and objects
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                
                # 2. Fix missing quotes around keys
                json_str = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)(\s*:)', r'\1"\2"\3', json_str)
                
                # 3. Fix single quotes used instead of double quotes
                # This is tricky because we need to avoid replacing single quotes in text
                # For simplicity, we'll just try both versions
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Try replacing all single quotes with double quotes
                    json_str = json_str.replace("'", '"')
                    return json.loads(json_str)
        except Exception:
            logger.debug("JSON error correction failed")
        
        # If all methods fail, return None
        return None
    
    def analyze_receipt(self, image_path):
        """Analyze a receipt image using Ollama vision model
        
        Args:
            image_path (str): Path to the receipt image
            
        Returns:
            dict: Extracted data from the receipt or error information
        """
        try:
            # First, classify the receipt to determine the best prompt
            from app.utils.receipt_classifier import classify_receipt
            classification = classify_receipt(image_path)
            receipt_type = classification.get('receipt_type', 'unknown')
            source_type = classification.get('source_type', 'unknown')
            
            logger.info(f"Receipt classified as: {receipt_type}, source: {source_type}")
            
            # Select the appropriate prompt based on receipt type
            if receipt_type == 'walmart':
                prompt = self._get_walmart_receipt_prompt()
            elif receipt_type in ['thrift_store', 'goodwill', 'salvation_army']:
                prompt = self._get_thrift_store_receipt_prompt()
            elif receipt_type in ['restaurant', 'cafe']:
                prompt = self._get_restaurant_receipt_prompt()
            elif receipt_type in ['amazon', 'ebay', 'etsy']:
                prompt = self._get_online_marketplace_receipt_prompt()
            else:
                # If receipt type is unknown, use source type
                if source_type == 'screenshot':
                    prompt = self._get_screenshot_receipt_prompt()
                elif source_type == 'photo':
                    prompt = self._get_photo_receipt_prompt()
                else:
                    # Fall back to generic prompt
                    prompt = self._get_generic_receipt_prompt()
            
            # Add receipt type context to the prompt
            prompt_with_context = f"This is a {receipt_type} receipt (source type: {source_type}). {prompt}"
            
            # Add stronger instructions for JSON-only response
            prompt_with_context += """
            
            CRITICAL: Your response must ONLY contain a valid JSON object. Do not include any explanatory text, markdown formatting, or code blocks before or after the JSON. The response should start with '{' and end with '}' with no other characters.
            """
            
            # Prepare prompt for receipt analysis - using the direct function call as shown in the documentation
            try:
                # Use the direct ollama.chat() function as shown in the documentation
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{
                        'role': 'user',
                        'content': prompt_with_context,
                        'images': [image_path]
                    }]
                )
                
                # Extract response content
                response_text = response['message']['content']
                
                # Extract JSON from the response using our robust method
                extracted_data = self._extract_json_from_text(response_text)
                if extracted_data:
                    return self._format_extracted_data(extracted_data)
                else:
                    logger.error("No valid JSON found in Ollama response")
                    return {'error': 'No valid JSON found in response', 'raw_response': response_text}
                
            except ollama.ResponseError as e:
                logger.error(f"Ollama API error: {e.error}")
                return {'error': f'API error: {e.status_code}', 'details': e.error}
                
        except Exception as e:
            logger.error(f"Error in Ollama vision analysis: {str(e)}")
            return {'error': str(e)}
    
    def _format_extracted_data(self, data):
        """Format the extracted data to match the application's expected structure
        
        Args:
            data (dict): Raw extracted data from Ollama
            
        Returns:
            dict: Formatted data
        """
        # Convert string values to appropriate types
        formatted_data = {
            'vendor': data.get('vendor'),
            'date': data.get('date'),
            'invoice_number': data.get('invoice_number'),
            'total': self._parse_float(data.get('total')),
            'tax_amount': self._parse_float(data.get('tax_amount')),
            'shipping_cost': self._parse_float(data.get('shipping_cost')),
            'platform_fee': self._parse_float(data.get('platform_fee')),
            'platform_name': data.get('platform_name'),
            'platform_url': data.get('platform_url'),
            'items': []
        }
        
        # Process items
        items = data.get('items', [])
        if isinstance(items, list):
            for item in items:
                formatted_item = {
                    'quantity': self._parse_int(item.get('quantity', 1)),
                    'name': item.get('name', '').strip(),
                    'price': self._parse_float(item.get('price')),
                    'condition': None,  # Will be determined by validation_rules
                    'sku': None         # Will be determined by validation_rules
                }
                formatted_data['items'].append(formatted_item)
        
        return formatted_data
    
    def _parse_float(self, value):
        """Safely parse a float value"""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
            
        try:
            # Remove currency symbols and commas
            if isinstance(value, str):
                value = value.replace('$', '').replace(',', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_int(self, value):
        """Safely parse an integer value"""
        if value is None:
            return 1  # Default quantity
            
        if isinstance(value, int):
            return value
            
        try:
            return int(value)
        except (ValueError, TypeError):
            return 1  # Default quantity
            
    # Specialized prompt methods for different receipt types
    
    def _get_generic_receipt_prompt(self):
        """Get a generic prompt for receipt analysis"""
        return """
        Extract the following information in JSON format:
        1. vendor – The store or vendor name (e.g., "Walmart").
        2. date – The purchase date (e.g., "07/28/17").
            -- If the exact format is unclear, choose the most obvious date string.
        3. invoice_number – The transaction or receipt number.
            -- Look for labels like "Ref #," "Trans ID," "TC#," or "Receipt #."
        4. total – The total amount paid (numeric value, e.g., 98.21).
        5. tax_amount – The tax amount (numeric value, e.g., 4.59).
        6. shipping_cost – If there is a shipping fee listed, extract it; otherwise, use null.
        7. platform_fee – If there is a platform or service fee listed, extract it; otherwise, use null.
        8. platform_name – If this is from an online marketplace, extract the platform name; otherwise, use null.
        9. platform_url – If a website URL is visible, extract it; otherwise, use null.
        10. items – A list of items purchased. For each item, include:
                - quantity – If the receipt explicitly shows a quantity, use it; otherwise, default to 1.
                - name – The item's name or description.
                - price – The line-item's price.
        
        Return ONLY a valid JSON object with these fields. If a field is not found, set it to null.
        Format the JSON like this:
        {
            "vendor": "...",
            "date": "...",
            "invoice_number": "...",
            "total": 0.00,
            "tax_amount": 0.00,
            "shipping_cost": 0.00,
            "platform_fee": 0.00,
            "platform_name": null,
            "platform_url": null,
            "items": [
                {
                    "quantity": 1,
                    "name": "...",
                    "price": 0.00
                }
            ]
        }
        
        IMPORTANT: Your response must ONLY contain the JSON object. Do not include any explanatory text, markdown formatting, or code blocks. The response should start with '{' and end with '}' with no other characters.
        """
    
    def _get_walmart_receipt_prompt(self):
        """Get a specialized prompt for Walmart receipts"""
        return """
        Extract the following information from this Walmart receipt in JSON format:
        
        1. vendor – Should be "Walmart" or the specific Walmart store name.
        2. date – The purchase date, typically found at the top of the receipt.
        3. invoice_number – Look for "TC#" or "Receipt #" followed by numbers.
        4. total – Look for "TOTAL" or "AMOUNT" followed by the total amount.
        5. tax_amount – Look for "TAX" followed by the amount.
        6. items – Pay special attention to the item list format:
           - Walmart receipts typically list items with the item name on one line
           - The price appears at the right side of the same line or on the next line
           - Some items may have a quantity indicator like "2 @" before the item name
           - Look for patterns like "ITEM NAME    $PRICE" or "QTY @ PRICE    ITEM NAME"
        
        For each item, extract:
        - quantity – Look for numbers before the item name, often followed by "@". Default to 1 if not found.
        - name – The item description, which may include brand names and product details.
        - price – The price for the item (for the total quantity, not per unit).
        
        Return ONLY a valid JSON object with these fields. If a field is not found, set it to null.
        Format the JSON like this:
        {
            "vendor": "Walmart",
            "date": "...",
            "invoice_number": "...",
            "total": 0.00,
            "tax_amount": 0.00,
            "shipping_cost": null,
            "platform_fee": null,
            "platform_name": null,
            "platform_url": null,
            "items": [
                {
                    "quantity": 1,
                    "name": "...",
                    "price": 0.00
                }
            ]
        }
        
        IMPORTANT: Your response must ONLY contain the JSON object. Do not include any explanatory text, markdown formatting, or code blocks. The response should start with '{' and end with '}' with no other characters.
        """
    
    def _get_thrift_store_receipt_prompt(self):
        """Get a specialized prompt for thrift store receipts"""
        return """
        Extract the following information from this thrift store receipt in JSON format:
        
        1. vendor – The thrift store name (e.g., "Goodwill", "Salvation Army", etc.).
        2. date – The purchase date, which may be in various formats.
        3. invoice_number – Look for "Receipt #" or similar indicators.
        4. total – The total amount paid, usually at the bottom of the receipt.
        5. tax_amount – The tax amount, if listed.
        
        For the items section, note that thrift store receipts:
        - Often have very simple item descriptions (e.g., "SHIRT", "PANTS", "BOOK")
        - May use category codes instead of detailed descriptions
        - Typically don't include brand names or detailed product information
        - May have handwritten elements or stamps
        - Often don't include quantities (assume 1 for each line item)
        
        For each item, extract:
        - quantity – Usually 1 unless explicitly stated
        - name – The item category or brief description
        - price – The price for the item
        
        Return ONLY a valid JSON object with these fields. If a field is not found, set it to null.
        Format the JSON like this:
        {
            "vendor": "...",
            "date": "...",
            "invoice_number": "...",
            "total": 0.00,
            "tax_amount": 0.00,
            "shipping_cost": null,
            "platform_fee": null,
            "platform_name": null,
            "platform_url": null,
            "items": [
                {
                    "quantity": 1,
                    "name": "...",
                    "price": 0.00
                }
            ]
        }
        
        IMPORTANT: Your response must ONLY contain the JSON object. Do not include any explanatory text, markdown formatting, or code blocks. The response should start with '{' and end with '}' with no other characters.
        """
    
    def _get_restaurant_receipt_prompt(self):
        """Get a specialized prompt for restaurant receipts"""
        return """
        Extract the following information from this restaurant receipt in JSON format:
        
        1. vendor – The restaurant name.
        2. date – The purchase date, typically at the top or bottom of the receipt.
        3. invoice_number – Look for "Check #", "Order #", or similar indicators.
        4. total – The total amount paid, usually at the bottom after tax and tip.
        5. tax_amount – The tax amount.
        
        For the items section, note that restaurant receipts:
        - List food and beverage items, often with brief descriptions
        - May include modifiers or special instructions indented below the main item
        - Sometimes group items by category (appetizers, entrees, drinks)
        - May include a subtotal before tax and tip
        
        For each item, extract:
        - quantity – Usually indicated at the beginning of the line, default to 1 if not specified
        - name – The food or beverage item name
        - price – The price for the item (for the total quantity)
        
        Return ONLY a valid JSON object with these fields. If a field is not found, set it to null.
        Format the JSON like this:
        {
            "vendor": "...",
            "date": "...",
            "invoice_number": "...",
            "total": 0.00,
            "tax_amount": 0.00,
            "shipping_cost": null,
            "platform_fee": null,
            "platform_name": null,
            "platform_url": null,
            "items": [
                {
                    "quantity": 1,
                    "name": "...",
                    "price": 0.00
                }
            ]
        }
        
        IMPORTANT: Your response must ONLY contain the JSON object. Do not include any explanatory text, markdown formatting, or code blocks. The response should start with '{' and end with '}' with no other characters.
        """
    
    def _get_online_marketplace_receipt_prompt(self):
        """Get a specialized prompt for online marketplace receipts"""
        return """
        Extract the following information from this online marketplace receipt in JSON format:
        
        1. vendor – The seller's name, which may be different from the platform.
        2. date – The purchase or order date.
        3. invoice_number – Look for "Order #", "Transaction ID", or similar indicators.
        4. total – The total amount paid, including all fees and shipping.
        5. tax_amount – The tax amount.
        6. shipping_cost – The shipping or delivery fee.
        7. platform_fee – Any service fees, processing fees, or platform fees.
        8. platform_name – The name of the marketplace (e.g., "Amazon", "eBay", "Etsy").
        9. platform_url – The website URL if visible.
        
        For the items section, note that online marketplace receipts:
        - Often include detailed item descriptions
        - May show item numbers or SKUs
        - Usually include shipping information
        - May have multiple sellers in a single order
        
        For each item, extract:
        - quantity – The number of items purchased
        - name – The product name/description
        - price – The total price for the item (quantity × unit price)
        
        Return ONLY a valid JSON object with these fields. If a field is not found, set it to null.
        Format the JSON like this:
        {
            "vendor": "...",
            "date": "...",
            "invoice_number": "...",
            "total": 0.00,
            "tax_amount": 0.00,
            "shipping_cost": 0.00,
            "platform_fee": 0.00,
            "platform_name": "...",
            "platform_url": "...",
            "items": [
                {
                    "quantity": 1,
                    "name": "...",
                    "price": 0.00
                }
            ]
        }
        
        IMPORTANT: Your response must ONLY contain the JSON object. Do not include any explanatory text, markdown formatting, or code blocks. The response should start with '{' and end with '}' with no other characters.
        """
    
    def _get_screenshot_receipt_prompt(self):
        """Get a specialized prompt for screenshot receipts"""
        return """
        Extract the following information from this screenshot of a receipt in JSON format:
        
        1. vendor – The store or website name.
        2. date – The purchase date.
        3. invoice_number – The order or transaction number.
        4. total – The total amount paid.
        5. tax_amount – The tax amount if shown.
        6. shipping_cost – Any shipping or delivery fees.
        7. platform_fee – Any service or platform fees.
        8. platform_name – If this is from an online platform, extract the name.
        9. platform_url – Any website URL visible in the screenshot.
        
        For the items section, note that screenshots:
        - May include browser elements, UI components, or cursor
        - Often have very clear text due to digital origin
        - May show only part of a receipt if it's a partial screenshot
        - Could be from email confirmations, order pages, or digital receipts
        
        For each item, extract:
        - quantity – The number of items
        - name – The product name/description
        - price – The price for the item
        
        Return ONLY a valid JSON object with these fields. If a field is not found, set it to null.
        Format the JSON like this:
        {
            "vendor": "...",
            "date": "...",
            "invoice_number": "...",
            "total": 0.00,
            "tax_amount": 0.00,
            "shipping_cost": 0.00,
            "platform_fee": 0.00,
            "platform_name": "...",
            "platform_url": "...",
            "items": [
                {
                    "quantity": 1,
                    "name": "...",
                    "price": 0.00
                }
            ]
        }
        
        IMPORTANT: Your response must ONLY contain the JSON object. Do not include any explanatory text, markdown formatting, or code blocks. The response should start with '{' and end with '}' with no other characters.
        """
    
    def _get_photo_receipt_prompt(self):
        """Get a specialized prompt for photo receipts"""
        return """
        Extract the following information from this photo of a receipt in JSON format:
        
        1. vendor – The store or vendor name.
        2. date – The purchase date.
        3. invoice_number – The receipt or transaction number.
        4. total – The total amount paid.
        5. tax_amount – The tax amount.
        6. shipping_cost – Any shipping fees (likely zero for in-store purchases).
        
        For the items section, note that photos of receipts:
        - May have lighting issues, shadows, or glare
        - Could be taken at an angle
        - Might have fingers or other objects partially obscuring content
        - Often have thermal paper fading or damage
        
        For each item, extract:
        - quantity – The number of items, default to 1 if not specified
        - name – The product name/description
        - price – The price for the item
        
        Return ONLY a valid JSON object with these fields. If a field is not found, set it to null.
        Format the JSON like this:
        {
            "vendor": "...",
            "date": "...",
            "invoice_number": "...",
            "total": 0.00,
            "tax_amount": 0.00,
            "shipping_cost": 0.00,
            "platform_fee": null,
            "platform_name": null,
            "platform_url": null,
            "items": [
                {
                    "quantity": 1,
                    "name": "...",
                    "price": 0.00
                }
            ]
        }
        
        IMPORTANT: Your response must ONLY contain the JSON object. Do not include any explanatory text, markdown formatting, or code blocks. The response should start with '{' and end with '}' with no other characters.
        """
    
    def refine_extracted_data(self, extracted_data, ocr_text=None):
        """Refine the extracted data using a second LLM call to clean up results
        
        Args:
            extracted_data (dict): Data extracted from the first LLM call
            ocr_text (str, optional): OCR text for additional context
            
        Returns:
            dict: Refined data with improved accuracy
        """
        try:
            # Convert extracted data to JSON string
            extracted_json = json.dumps(extracted_data, indent=2)
            
            # Prepare prompt for refining the extracted data
            prompt = f"""
            I need you to refine and clean up the following extracted receipt data. 
            The data may contain errors, duplicates, or header information mistakenly identified as items.
            
            Here is the extracted data:
            ```json
            {extracted_json}
            ```
            
            Please analyze this data and fix the following issues:
            1. Remove any duplicate items (items with the same name but possibly different prices)
            2. Remove any header information mistakenly identified as items (e.g., "Item Description", "Qty", "Price", etc.)
            3. Fix any obvious errors in item names, quantities, or prices
            4. Ensure the total amount makes sense given the items and tax
            5. Remove any items that are clearly not actual products (e.g., store policies, return information, etc.)
            6. Standardize item names by removing unnecessary prefixes, suffixes, or codes
            7. Correct any OCR errors in text fields (vendor name, item descriptions, etc.)
            8. Ensure numeric values (prices, quantities) are reasonable and consistent
            
            Return ONLY a valid JSON object with the same structure as the input, but with the issues fixed.
            The JSON should include: vendor, date, invoice_number, total, tax_amount, shipping_cost, platform_fee, platform_name, platform_url, and items array.
            Each item should have: quantity, name, and price.
            
            IMPORTANT: Your response must ONLY contain the JSON object. Do not include any explanatory text, markdown formatting, or code blocks. The response should start with '{' and end with '}' with no other characters.
            """
            
            # Add OCR text if available for additional context
            if ocr_text:
                prompt += f"\n\nHere is the OCR text from the receipt for additional context:\n```\n{ocr_text}\n```"
            
            # Use the direct ollama.chat() function as shown in the documentation
            try:
                response = ollama.chat(
                    model=self.model_name,
                    messages=[{
                        'role': 'user',
                        'content': prompt
                    }]
                )
                
                # Extract response content
                response_text = response['message']['content']
                
                # Extract JSON from the response using our robust method
                refined_data = self._extract_json_from_text(response_text)
                if refined_data:
                    return self._format_extracted_data(refined_data)
                else:
                    logger.error("No valid JSON found in refinement response")
                    return extracted_data  # Return original data if refinement failed
                
            except ollama.ResponseError as e:
                logger.error(f"Ollama API error during refinement: {e.error}")
                return extracted_data  # Return original data if refinement failed
                
        except Exception as e:
            logger.error(f"Error in refining extracted data: {str(e)}")
            return extracted_data  # Return original data if refinement failed
