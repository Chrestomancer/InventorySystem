import logging
import os
import gc
import numpy as np
from PIL import Image

# Global reader instance to avoid reloading the model each time
_easyocr_reader = None

def get_easyocr_reader():
    """Get or initialize the EasyOCR reader"""
    global _easyocr_reader
    if _easyocr_reader is None:
        try:
            import easyocr
            _easyocr_reader = easyocr.Reader(['en'], gpu=True)  # Using GPU for faster processing
            logging.info("EasyOCR reader initialized")
        except Exception as e:
            logging.error(f"Error initializing EasyOCR reader: {str(e)}")
            return None
    return _easyocr_reader

def resize_image_if_needed(image_path, max_size=1600):
    """Resize image if it's too large to reduce memory usage"""
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        # Check if image is too large
        if width > max_size or height > max_size:
            # Calculate new dimensions while preserving aspect ratio
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            # Resize image (using a resampling filter that works in all Pillow versions)
            # In newer Pillow versions, ANTIALIAS is renamed to LANCZOS
            resampling_filter = getattr(Image, 'LANCZOS', getattr(Image, 'ANTIALIAS', Image.BICUBIC))
            img = img.resize((new_width, new_height), resampling_filter)
            
            # Save resized image with a suffix
            filename, ext = os.path.splitext(image_path)
            resized_path = f"{filename}_resized{ext}"
            img.save(resized_path)
            
            logging.info(f"Image resized from {width}x{height} to {new_width}x{new_height}")
            return resized_path
        
        return image_path
    except Exception as e:
        logging.error(f"Error resizing image: {str(e)}")
        return image_path

def perform_easyocr(image_path, detail_level='high'):
    """Extract text using EasyOCR with memory management"""
    try:
        # Get reader
        reader = get_easyocr_reader()
        if reader is None:
            return {'error': 'Failed to initialize EasyOCR reader', 'engine': 'easyocr'}
        
        # Set OCR parameters based on detail level
        paragraph = False
        if detail_level == 'high':
            # For receipts, we want to detect each line separately
            paragraph = False
        elif detail_level == 'medium':
            # For general documents, paragraph mode can be useful
            paragraph = True
        
        # Process image with appropriate settings
        results = reader.readtext(image_path, paragraph=paragraph, detail=1, 
                                 width_ths=0.7, height_ths=0.7, 
                                 slope_ths=0.3, ycenter_ths=0.5)
        
        text_elements = []
        full_text = ""
        
        for (bbox, text, prob) in results:
            # Skip empty or very low confidence results
            if not text.strip() or prob < 0.1:
                continue
                
            text_elements.append({
                'text': text,
                'confidence': prob,
                'position': {
                    'top_left': bbox[0],
                    'top_right': bbox[1],
                    'bottom_right': bbox[2],
                    'bottom_left': bbox[3]
                }
            })
            full_text += text + " "
        
        # Force garbage collection to free memory
        gc.collect()
        
        return {
            'full_text': full_text,
            'text_elements': text_elements,
            'engine': 'easyocr'
        }
    except Exception as e:
        logging.error(f"EasyOCR error: {str(e)}")
        # Force garbage collection
        gc.collect()
        return {'error': str(e), 'engine': 'easyocr'}

def try_multiple_preprocessed_versions(preprocessed_images):
    """Try OCR on multiple preprocessed versions of the image"""
    best_result = None
    best_score = 0
    
    # Try each preprocessed version
    for version_name, image_path in preprocessed_images.items():
        if version_name == 'original':
            # Skip original for now, we'll use it as fallback
            continue
            
        # Process with EasyOCR
        result = perform_easyocr(image_path)
        
        if 'error' in result:
            logging.error(f"Error processing {version_name}: {result['error']}")
            continue
        
        # Calculate a score based on text length and average confidence
        text_length = len(result.get('full_text', ''))
        avg_confidence = 0
        if result.get('text_elements'):
            confidences = [elem.get('confidence', 0) for elem in result.get('text_elements', [])]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
        
        # Score is a combination of text length and confidence
        score = text_length * avg_confidence
        
        logging.info(f"Version {version_name}: score={score}, text_length={text_length}, avg_confidence={avg_confidence}")
        
        # Keep the best result
        if score > best_score:
            best_score = score
            best_result = result
            best_result['preprocessing_version'] = version_name
    
    # If all preprocessed versions failed, try the original
    if best_result is None:
        logging.info("All preprocessed versions failed, trying original image")
        best_result = perform_easyocr(preprocessed_images['original'])
        best_result['preprocessing_version'] = 'original'
    
    return best_result

def perform_multi_engine_ocr(image_path):
    """Extract text using OCR engines (simplified to just use EasyOCR)"""
    # Just use EasyOCR for stability
    return perform_easyocr(image_path)
