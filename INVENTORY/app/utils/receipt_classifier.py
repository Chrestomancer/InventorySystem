import cv2
import numpy as np
import re
import logging
import os
from collections import Counter

class ReceiptClassifier:
    """
    Classifies receipts based on visual and textual features to determine
    the receipt type (e.g., Walmart, thrift store) and format (e.g., printed, handwritten).
    """
    
    # Common store patterns to look for in text
    STORE_PATTERNS = {
        'walmart': [r'walmart', r'wal-?mart', r'w(?:al)?m(?:ar)?t'],
        'target': [r'target', r'target\.com'],
        'costco': [r'costco', r'wholesale'],
        'amazon': [r'amazon', r'amazon\.com', r'amzn'],
        'ebay': [r'ebay', r'ebay\.com'],
        'goodwill': [r'goodwill', r'good\s*will'],
        'salvation_army': [r'salvation\s*army'],
        'thrift_store': [r'thrift', r'second\s*hand', r'2nd\s*hand', r'consignment'],
        'dollar_store': [r'dollar\s*(?:general|tree|store)', r'\$\s*tree'],
        'grocery': [r'grocery', r'supermarket', r'market', r'foods'],
        'restaurant': [r'restaurant', r'cafe', r'diner', r'grill', r'kitchen', r'bar', r'bistro']
    }
    
    # Receipt format patterns
    FORMAT_PATTERNS = {
        'printed': [
            r'subtotal', r'tax', r'total', r'change', r'cash', r'credit\s*card',
            r'debit', r'payment', r'balance', r'due', r'receipt', r'invoice',
            r'transaction', r'sale', r'purchase', r'order', r'customer', r'cashier',
            r'terminal', r'register', r'store', r'location', r'date', r'time'
        ],
        'handwritten': [
            # Less structured, fewer standard terms, often missing elements
            # Handwritten receipts often have fewer matches with standard terms
        ]
    }
    
    def __init__(self):
        """Initialize the receipt classifier"""
        logging.info("Initializing receipt classifier")
    
    def classify(self, image_path, ocr_text=None):
        """
        Classify the receipt type and format
        
        Args:
            image_path (str): Path to the receipt image
            ocr_text (str, optional): Pre-extracted OCR text if available
            
        Returns:
            dict: Classification results with receipt type, format, and confidence scores
        """
        # Load the image
        try:
            image = cv2.imread(image_path)
            if image is None:
                logging.error(f"Failed to read image: {image_path}")
                return self._default_classification()
        except Exception as e:
            logging.error(f"Error loading image for classification: {str(e)}")
            return self._default_classification()
        
        # Extract visual features
        visual_features = self._extract_visual_features(image)
        
        # Get OCR text if not provided
        if ocr_text is None:
            ocr_text = self._get_ocr_text(image_path)
        
        # Classify based on text content
        text_classification = self._classify_from_text(ocr_text)
        
        # Classify based on visual features
        visual_classification = self._classify_from_visual(visual_features)
        
        # Determine source type (screenshot, photo, scan)
        source_type = self._determine_source_type(image, visual_features)
        
        # Combine classifications with confidence scores
        combined_classification = self._combine_classifications(
            text_classification, 
            visual_classification,
            source_type
        )
        
        logging.info(f"Receipt classified as: {combined_classification}")
        return combined_classification
    
    def _extract_visual_features(self, image):
        """
        Extract visual features from the receipt image
        
        Args:
            image: OpenCV image object
            
        Returns:
            dict: Visual features extracted from the image
        """
        features = {}
        
        # Get image dimensions
        height, width = image.shape[:2]
        features['aspect_ratio'] = width / height if height > 0 else 0
        features['size'] = (width, height)
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Calculate average brightness
        features['avg_brightness'] = np.mean(gray)
        
        # Calculate contrast
        features['contrast'] = np.std(gray)
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        features['edge_density'] = np.sum(edges) / (width * height)
        
        # Detect lines (horizontal and vertical)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
        if lines is not None:
            horizontal_lines = 0
            vertical_lines = 0
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if abs(x2 - x1) > abs(y2 - y1):
                    horizontal_lines += 1
                else:
                    vertical_lines += 1
            
            features['horizontal_lines'] = horizontal_lines
            features['vertical_lines'] = vertical_lines
            features['line_ratio'] = horizontal_lines / vertical_lines if vertical_lines > 0 else float('inf')
        else:
            features['horizontal_lines'] = 0
            features['vertical_lines'] = 0
            features['line_ratio'] = 0
        
        # Check for color or black and white
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = hsv[:,:,1]
        features['avg_saturation'] = np.mean(saturation)
        features['is_color'] = features['avg_saturation'] > 30
        
        # Detect text regions (approximation using edge density in regions)
        features['text_regions'] = self._detect_text_regions(gray)
        
        return features
    
    def _detect_text_regions(self, gray_image):
        """
        Detect potential text regions in the image
        
        Args:
            gray_image: Grayscale image
            
        Returns:
            int: Estimated number of text regions
        """
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size to find potential text regions
        text_regions = 0
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            
            # Text regions typically have certain aspect ratios and sizes
            if 0.1 < aspect_ratio < 15 and 10 < w < 500 and 5 < h < 100:
                text_regions += 1
        
        return text_regions
    
    def _get_ocr_text(self, image_path):
        """
        Get OCR text from the image using EasyOCR
        
        Args:
            image_path: Path to the image
            
        Returns:
            str: Extracted text or empty string if OCR fails
        """
        try:
            # Import here to avoid circular imports
            from app.utils.ocr_engines import perform_easyocr
            
            # Perform OCR
            ocr_result = perform_easyocr(image_path)
            
            if 'error' in ocr_result:
                logging.error(f"OCR error in receipt classification: {ocr_result['error']}")
                return ""
            
            return ocr_result.get('full_text', "")
        except Exception as e:
            logging.error(f"Error performing OCR for classification: {str(e)}")
            return ""
    
    def _classify_from_text(self, text):
        """
        Classify receipt based on text content
        
        Args:
            text (str): OCR text from the receipt
            
        Returns:
            dict: Classification results based on text
        """
        if not text:
            return {'store_type': 'unknown', 'confidence': 0.0}
        
        text = text.lower()
        
        # Check for store patterns
        store_matches = {}
        for store_type, patterns in self.STORE_PATTERNS.items():
            store_matches[store_type] = 0
            for pattern in patterns:
                matches = re.findall(pattern, text)
                store_matches[store_type] += len(matches)
        
        # Check for format patterns
        format_matches = {}
        for format_type, patterns in self.FORMAT_PATTERNS.items():
            format_matches[format_type] = 0
            for pattern in patterns:
                matches = re.findall(pattern, text)
                format_matches[format_type] += len(matches)
        
        # Determine store type
        best_store = max(store_matches.items(), key=lambda x: x[1])
        store_type = best_store[0] if best_store[1] > 0 else 'unknown'
        
        # Calculate confidence based on number of matches
        total_matches = sum(store_matches.values())
        confidence = best_store[1] / max(total_matches, 1)
        
        # Determine format type
        best_format = max(format_matches.items(), key=lambda x: x[1])
        format_type = best_format[0] if best_format[1] > 0 else 'unknown'
        
        # Calculate format confidence
        total_format_matches = sum(format_matches.values())
        format_confidence = best_format[1] / max(total_format_matches, 1)
        
        # Check for specific receipt structures
        structure_type = self._identify_receipt_structure(text)
        
        return {
            'store_type': store_type,
            'confidence': confidence,
            'format_type': format_type,
            'format_confidence': format_confidence,
            'structure_type': structure_type
        }
    
    def _identify_receipt_structure(self, text):
        """
        Identify the structure type of the receipt
        
        Args:
            text (str): OCR text from the receipt
            
        Returns:
            str: Structure type (itemized, simple, etc.)
        """
        # Check for itemized receipt (items with prices)
        itemized_patterns = [
            r'\d+\s+[\w\s]+\s+\d+\.\d{2}',  # Quantity, item, price
            r'[\w\s]+\s+\d+\.\d{2}'         # Item, price
        ]
        
        for pattern in itemized_patterns:
            matches = re.findall(pattern, text)
            if len(matches) > 3:  # Multiple items found
                return 'itemized'
        
        # Check for simple receipt (just total)
        if re.search(r'total\s*\$?\s*\d+\.\d{2}', text, re.IGNORECASE):
            return 'simple'
        
        return 'unknown'
    
    def _classify_from_visual(self, features):
        """
        Classify receipt based on visual features
        
        Args:
            features (dict): Visual features extracted from the image
            
        Returns:
            dict: Classification results based on visual features
        """
        # Initialize classification
        classification = {
            'visual_type': 'unknown',
            'visual_confidence': 0.0
        }
        
        # Check for Walmart receipt characteristics
        walmart_score = 0
        
        # Walmart receipts typically have a specific aspect ratio
        if 0.2 < features['aspect_ratio'] < 0.4:
            walmart_score += 0.3
        
        # Walmart receipts typically have many horizontal lines
        if features.get('horizontal_lines', 0) > 10:
            walmart_score += 0.2
        
        # Walmart receipts are typically black and white
        if not features.get('is_color', True):
            walmart_score += 0.2
        
        # Thrift store receipt characteristics
        thrift_score = 0
        
        # Thrift store receipts often have fewer lines
        if features.get('horizontal_lines', 0) < 5:
            thrift_score += 0.2
        
        # Thrift store receipts often have simpler structure
        if features.get('text_regions', 0) < 20:
            thrift_score += 0.3
        
        # Restaurant receipt characteristics
        restaurant_score = 0
        
        # Restaurant receipts often have a specific aspect ratio
        if 0.3 < features['aspect_ratio'] < 0.5:
            restaurant_score += 0.2
        
        # Restaurant receipts often have fewer text regions
        if 10 < features.get('text_regions', 0) < 30:
            restaurant_score += 0.2
        
        # Determine the best match
        scores = {
            'walmart': walmart_score,
            'thrift_store': thrift_score,
            'restaurant': restaurant_score
        }
        
        best_type = max(scores.items(), key=lambda x: x[1])
        
        if best_type[1] > 0.3:  # Minimum threshold for confidence
            classification['visual_type'] = best_type[0]
            classification['visual_confidence'] = best_type[1]
        
        return classification
    
    def _determine_source_type(self, image, features):
        """
        Determine if the receipt is a screenshot, photo, or scan
        
        Args:
            image: OpenCV image object
            features (dict): Visual features extracted from the image
            
        Returns:
            dict: Source type classification
        """
        # Initialize source type
        source_type = {
            'type': 'unknown',
            'confidence': 0.0
        }
        
        # Screenshot characteristics
        screenshot_score = 0
        
        # Screenshots often have perfect horizontal/vertical lines
        if features.get('horizontal_lines', 0) > 5 and features.get('vertical_lines', 0) > 5:
            line_ratio = features.get('line_ratio', 0)
            if 0.8 < line_ratio < 1.2:  # Nearly equal horizontal and vertical lines
                screenshot_score += 0.3
        
        # Screenshots often have high contrast
        if features.get('contrast', 0) > 50:
            screenshot_score += 0.2
        
        # Screenshots often have specific aspect ratios
        if 1.3 < features['aspect_ratio'] < 2.0:
            screenshot_score += 0.2
        
        # Photo characteristics
        photo_score = 0
        
        # Photos often have uneven lighting
        brightness_variation = np.std(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        if brightness_variation > 40:
            photo_score += 0.3
        
        # Photos often have higher saturation
        if features.get('avg_saturation', 0) > 50:
            photo_score += 0.2
        
        # Photos often have fewer straight lines
        if features.get('horizontal_lines', 0) < 10 and features.get('vertical_lines', 0) < 10:
            photo_score += 0.2
        
        # Scan characteristics
        scan_score = 0
        
        # Scans often have uniform brightness
        if 20 < features.get('avg_brightness', 0) < 240 and brightness_variation < 30:
            scan_score += 0.3
        
        # Scans often have clear edges
        if features.get('edge_density', 0) > 0.05:
            scan_score += 0.2
        
        # Scans often have a specific aspect ratio
        if 0.6 < features['aspect_ratio'] < 1.5:
            scan_score += 0.2
        
        # Determine the best match
        scores = {
            'screenshot': screenshot_score,
            'photo': photo_score,
            'scan': scan_score
        }
        
        best_type = max(scores.items(), key=lambda x: x[1])
        
        if best_type[1] > 0.3:  # Minimum threshold for confidence
            source_type['type'] = best_type[0]
            source_type['confidence'] = best_type[1]
        
        return source_type
    
    def _combine_classifications(self, text_classification, visual_classification, source_type):
        """
        Combine text and visual classifications
        
        Args:
            text_classification (dict): Classification based on text
            visual_classification (dict): Classification based on visual features
            source_type (dict): Source type classification
            
        Returns:
            dict: Combined classification
        """
        # Start with text classification as base
        combined = {
            'receipt_type': text_classification.get('store_type', 'unknown'),
            'format_type': text_classification.get('format_type', 'unknown'),
            'structure_type': text_classification.get('structure_type', 'unknown'),
            'source_type': source_type.get('type', 'unknown')
        }
        
        # If text classification is unknown or low confidence, use visual
        if (combined['receipt_type'] == 'unknown' or 
            text_classification.get('confidence', 0) < 0.4) and \
           visual_classification.get('visual_type') != 'unknown':
            combined['receipt_type'] = visual_classification.get('visual_type')
        
        # Calculate overall confidence
        text_conf = text_classification.get('confidence', 0)
        visual_conf = visual_classification.get('visual_confidence', 0)
        source_conf = source_type.get('confidence', 0)
        
        # Weight text confidence higher than visual
        combined['confidence'] = (text_conf * 0.6) + (visual_conf * 0.3) + (source_conf * 0.1)
        
        return combined
    
    def _default_classification(self):
        """Return default classification when analysis fails"""
        return {
            'receipt_type': 'unknown',
            'format_type': 'unknown',
            'structure_type': 'unknown',
            'source_type': 'unknown',
            'confidence': 0.0
        }


# Helper function to classify a receipt
def classify_receipt(image_path, ocr_text=None):
    """
    Classify a receipt image
    
    Args:
        image_path (str): Path to the receipt image
        ocr_text (str, optional): Pre-extracted OCR text if available
        
    Returns:
        dict: Classification results
    """
    classifier = ReceiptClassifier()
    return classifier.classify(image_path, ocr_text)
