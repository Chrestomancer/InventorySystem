import cv2
import numpy as np
import os
import logging
import gc
import math
from app.utils.receipt_classifier import classify_receipt

def save_preprocessed_image(image, original_path, suffix):
    """Save a preprocessed image with a suffix"""
    filename, ext = os.path.splitext(original_path)
    output_path = f"{filename}_{suffix}{ext}"
    cv2.imwrite(output_path, image)
    return output_path

def preprocess_grayscale(image_path):
    """Convert image to grayscale"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            logging.error(f"Failed to read image: {image_path}")
            return image_path
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        result = save_preprocessed_image(gray, image_path, "gray")
        
        # Release memory
        del img, gray
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in grayscale preprocessing: {str(e)}")
        return image_path

def preprocess_adaptive_threshold(image_path):
    """Apply adaptive thresholding to image"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        result = save_preprocessed_image(thresh, image_path, "thresh")
        
        # Release memory
        del img, gray, thresh
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in adaptive threshold preprocessing: {str(e)}")
        return image_path

def preprocess_denoise(image_path):
    """Apply denoising to image"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
            
        # Apply denoising
        denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        result = save_preprocessed_image(denoised, image_path, "denoised")
        
        # Release memory
        del img, denoised
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in denoising: {str(e)}")
        return image_path

def preprocess_sharpen(image_path):
    """Sharpen image to improve text clarity"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        
        # Create sharpening kernel
        kernel = np.array([[-1,-1,-1], 
                           [-1, 9,-1],
                           [-1,-1,-1]])
        
        # Apply kernel
        sharpened = cv2.filter2D(img, -1, kernel)
        result = save_preprocessed_image(sharpened, image_path, "sharp")
        
        # Release memory
        del img, sharpened
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in sharpening: {str(e)}")
        return image_path

def preprocess_contrast_enhance(image_path):
    """Enhance contrast using CLAHE"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
            
        # Convert to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L-channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        
        # Merge channels
        limg = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        result = save_preprocessed_image(enhanced, image_path, "contrast")
        
        # Release memory
        del img, lab, l, a, b, cl, limg, enhanced
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in contrast enhancement: {str(e)}")
        return image_path

# New preprocessing functions for specific receipt types

def preprocess_perspective_correction(image_path):
    """Correct perspective distortion in receipt images"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply edge detection
        edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            logging.warning("No contours found for perspective correction")
            return image_path
            
        # Find the largest contour (assumed to be the receipt)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Approximate the contour to a polygon
        epsilon = 0.02 * cv2.arcLength(largest_contour, True)
        approx = cv2.approxPolyDP(largest_contour, epsilon, True)
        
        # If we don't get a quadrilateral, return original image
        if len(approx) != 4:
            logging.warning(f"Expected 4 corners for perspective correction, got {len(approx)}")
            return image_path
            
        # Order the points in top-left, top-right, bottom-right, bottom-left order
        pts = np.array([point[0] for point in approx])
        rect = np.zeros((4, 2), dtype="float32")
        
        # Top-left point has the smallest sum of coordinates
        # Bottom-right point has the largest sum
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # Top-right point has the smallest difference of coordinates
        # Bottom-left point has the largest difference
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        # Calculate width and height of the new image
        width_a = np.sqrt(((rect[2][0] - rect[3][0]) ** 2) + ((rect[2][1] - rect[3][1]) ** 2))
        width_b = np.sqrt(((rect[1][0] - rect[0][0]) ** 2) + ((rect[1][1] - rect[0][1]) ** 2))
        max_width = max(int(width_a), int(width_b))
        
        height_a = np.sqrt(((rect[1][0] - rect[2][0]) ** 2) + ((rect[1][1] - rect[2][1]) ** 2))
        height_b = np.sqrt(((rect[0][0] - rect[3][0]) ** 2) + ((rect[0][1] - rect[3][1]) ** 2))
        max_height = max(int(height_a), int(height_b))
        
        # Define destination points for the perspective transformation
        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype="float32")
        
        # Calculate the perspective transform matrix
        M = cv2.getPerspectiveTransform(rect, dst)
        
        # Apply the perspective transformation
        warped = cv2.warpPerspective(img, M, (max_width, max_height))
        
        result = save_preprocessed_image(warped, image_path, "perspective")
        
        # Release memory
        del img, gray, blurred, edges, warped
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in perspective correction: {str(e)}")
        return image_path

def preprocess_shadow_removal(image_path):
    """Remove shadows from receipt images"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to smooth the image while preserving edges
        smooth = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Apply morphological operations to estimate the background
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        bg = cv2.morphologyEx(smooth, cv2.MORPH_DILATE, kernel)
        
        # Divide the original image by the background to remove shadows
        diff = cv2.absdiff(smooth, bg)
        norm = cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)
        
        # Apply threshold to get binary image
        _, shadow_removed = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        result = save_preprocessed_image(shadow_removed, image_path, "shadow_removed")
        
        # Release memory
        del img, gray, smooth, bg, diff, norm, shadow_removed
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in shadow removal: {str(e)}")
        return image_path

def preprocess_glare_reduction(image_path):
    """Reduce glare in receipt images"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
            
        # Convert to HSV color space
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        
        # Identify glare areas (very high value and low saturation)
        _, glare_mask = cv2.threshold(v, 220, 255, cv2.THRESH_BINARY)
        
        # Dilate the glare mask to include surrounding areas
        kernel = np.ones((5, 5), np.uint8)
        glare_mask = cv2.dilate(glare_mask, kernel, iterations=1)
        
        # Reduce value in glare areas
        v_reduced = v.copy()
        v_reduced[glare_mask > 0] = v_reduced[glare_mask > 0] * 0.8
        
        # Increase saturation in glare areas
        s_increased = s.copy()
        s_increased[glare_mask > 0] = np.minimum(s_increased[glare_mask > 0] * 1.5, 255).astype(np.uint8)
        
        # Merge channels back
        hsv_reduced = cv2.merge([h, s_increased, v_reduced])
        reduced_glare = cv2.cvtColor(hsv_reduced, cv2.COLOR_HSV2BGR)
        
        result = save_preprocessed_image(reduced_glare, image_path, "glare_reduced")
        
        # Release memory
        del img, hsv, h, s, v, glare_mask, v_reduced, s_increased, hsv_reduced, reduced_glare
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in glare reduction: {str(e)}")
        return image_path

def preprocess_border_removal(image_path):
    """Remove borders from receipt images (especially for screenshots)"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return image_path
            
        # Find the largest contour (assumed to be the receipt)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Crop the image to the bounding rectangle
        cropped = img[y:y+h, x:x+w]
        
        result = save_preprocessed_image(cropped, image_path, "border_removed")
        
        # Release memory
        del img, gray, binary, cropped
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in border removal: {str(e)}")
        return image_path

def preprocess_deskew(image_path):
    """Correct skew in receipt images"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find all contours
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        # Calculate angles of all contours
        angles = []
        for contour in contours:
            if cv2.contourArea(contour) < 100:  # Skip very small contours
                continue
                
            # Fit a rotated rectangle around the contour
            rect = cv2.minAreaRect(contour)
            angle = rect[2]
            
            # Adjust angle to be between -45 and 45 degrees
            if angle < -45:
                angle += 90
            if angle > 45:
                angle -= 90
                
            angles.append(angle)
        
        if not angles:
            return image_path
            
        # Use the median angle to avoid outliers
        median_angle = np.median(angles)
        
        # Rotate the image to correct the skew
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        result = save_preprocessed_image(rotated, image_path, "deskewed")
        
        # Release memory
        del img, gray, binary, rotated
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in deskew: {str(e)}")
        return image_path

def preprocess_line_removal(image_path):
    """Remove horizontal and vertical lines that might interfere with text recognition"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Create kernels for horizontal and vertical lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
        
        # Detect horizontal lines
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Detect vertical lines
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # Combine horizontal and vertical lines
        lines = cv2.add(horizontal_lines, vertical_lines)
        
        # Remove lines from the original image
        result_binary = cv2.subtract(binary, lines)
        
        # Convert back to grayscale
        result_gray = cv2.bitwise_not(result_binary)
        
        result = save_preprocessed_image(result_gray, image_path, "lines_removed")
        
        # Release memory
        del img, gray, binary, horizontal_lines, vertical_lines, lines, result_binary, result_gray
        gc.collect()
        
        return result
    except Exception as e:
        logging.error(f"Error in line removal: {str(e)}")
        return image_path

def preprocess_walmart_receipt(image_path):
    """Apply specialized preprocessing for Walmart receipts"""
    try:
        # Walmart receipts typically benefit from:
        # 1. Grayscale conversion
        grayscale_path = preprocess_grayscale(image_path)
        
        # 2. Contrast enhancement with higher clip limit for better text visibility
        img = cv2.imread(grayscale_path)
        if img is None:
            return image_path
            
        # Ensure the image is single-channel grayscale before applying CLAHE
        if len(img.shape) > 2:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        # Apply stronger contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        contrast_path = save_preprocessed_image(enhanced, image_path, "walmart_contrast")
        
        # 3. Line removal to eliminate horizontal separators
        lines_removed_path = preprocess_line_removal(contrast_path)
        
        # 4. Adaptive thresholding with custom parameters
        img = cv2.imread(lines_removed_path)
        if img is None:
            return image_path
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) > 2 else img
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 15, 4  # Larger block size and higher C value
        )
        thresh_path = save_preprocessed_image(thresh, image_path, "walmart_thresh")
        
        # 5. Sharpen the image
        sharpened_path = preprocess_sharpen(thresh_path)
        
        # Return all processed versions
        return {
            'original': image_path,
            'grayscale': grayscale_path,
            'contrast': contrast_path,
            'lines_removed': lines_removed_path,
            'threshold': thresh_path,
            'sharpened': sharpened_path,
            'processed': sharpened_path  # Best version for OCR
        }
    except Exception as e:
        logging.error(f"Error in Walmart receipt preprocessing: {str(e)}")
        return {
            'original': image_path,
            'processed': image_path
        }

def preprocess_thrift_store_receipt(image_path):
    """Apply specialized preprocessing for thrift store receipts"""
    try:
        # Thrift store receipts typically benefit from:
        # 1. Perspective correction (often taken at an angle)
        perspective_path = preprocess_perspective_correction(image_path)
        
        # 2. Grayscale conversion
        grayscale_path = preprocess_grayscale(perspective_path)
        
        # 3. Stronger denoising (often printed on thermal paper with noise)
        img = cv2.imread(grayscale_path)
        if img is None:
            return image_path
            
        # Ensure the image is single-channel grayscale before denoising
        if len(img.shape) > 2:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        # Apply stronger denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, 15, 7, 21)
        denoised_path = save_preprocessed_image(denoised, image_path, "thrift_denoised")
        
        # 4. Contrast enhancement
        contrast_path = preprocess_contrast_enhance(denoised_path)
        
        # 5. Binary thresholding (often works better than adaptive for simple receipts)
        img = cv2.imread(contrast_path)
        if img is None:
            return image_path
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) > 2 else img
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh_path = save_preprocessed_image(thresh, image_path, "thrift_thresh")
        
        # Return all processed versions
        return {
            'original': image_path,
            'perspective': perspective_path,
            'grayscale': grayscale_path,
            'denoised': denoised_path,
            'contrast': contrast_path,
            'threshold': thresh_path,
            'processed': thresh_path  # Best version for OCR
        }
    except Exception as e:
        logging.error(f"Error in thrift store receipt preprocessing: {str(e)}")
        return {
            'original': image_path,
            'processed': image_path
        }

def preprocess_screenshot_receipt(image_path):
    """Apply specialized preprocessing for screenshot receipts"""
    try:
        # Screenshot receipts typically benefit from:
        # 1. Border removal
        border_removed_path = preprocess_border_removal(image_path)
        
        # 2. Grayscale conversion
        grayscale_path = preprocess_grayscale(border_removed_path)
        
        # 3. Contrast enhancement
        contrast_path = preprocess_contrast_enhance(grayscale_path)
        
        # 4. Adaptive thresholding with custom parameters for digital content
        img = cv2.imread(contrast_path)
        if img is None:
            return image_path
            
        # Ensure the image is single-channel grayscale before thresholding
        if len(img.shape) > 2:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
            cv2.THRESH_BINARY, 11, 5
        )
        thresh_path = save_preprocessed_image(thresh, image_path, "screenshot_thresh")
        
        # Return all processed versions
        return {
            'original': image_path,
            'border_removed': border_removed_path,
            'grayscale': grayscale_path,
            'contrast': contrast_path,
            'threshold': thresh_path,
            'processed': thresh_path  # Best version for OCR
        }
    except Exception as e:
        logging.error(f"Error in screenshot receipt preprocessing: {str(e)}")
        return {
            'original': image_path,
            'processed': image_path
        }

def preprocess_photo_receipt(image_path):
    """Apply specialized preprocessing for photo receipts"""
    try:
        # Photo receipts typically benefit from:
        # 1. Perspective correction
        perspective_path = preprocess_perspective_correction(image_path)
        
        # 2. Shadow removal
        shadow_removed_path = preprocess_shadow_removal(perspective_path)
        
        # 3. Glare reduction
        glare_reduced_path = preprocess_glare_reduction(shadow_removed_path)
        
        # 4. Grayscale conversion
        grayscale_path = preprocess_grayscale(glare_reduced_path)
        
        # 5. Denoising
        img = cv2.imread(grayscale_path)
        if img is None:
            return image_path
            
        # Ensure the image is single-channel grayscale before denoising
        if len(img.shape) > 2:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
            
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        denoised_path = save_preprocessed_image(denoised, image_path, "photo_denoised")
        
        # 6. Contrast enhancement
        contrast_path = preprocess_contrast_enhance(denoised_path)
        
        # 7. Adaptive thresholding
        thresh_path = preprocess_adaptive_threshold(contrast_path)
        
        # 8. Sharpen the image
        sharpened_path = preprocess_sharpen(thresh_path)
        
        # Return all processed versions
        return {
            'original': image_path,
            'perspective': perspective_path,
            'shadow_removed': shadow_removed_path,
            'glare_reduced': glare_reduced_path,
            'grayscale': grayscale_path,
            'denoised': denoised_path,
            'contrast': contrast_path,
            'threshold': thresh_path,
            'sharpened': sharpened_path,
            'processed': sharpened_path  # Best version for OCR
        }
    except Exception as e:
        logging.error(f"Error in photo receipt preprocessing: {str(e)}")
        return {
            'original': image_path,
            'processed': image_path
        }

def apply_best_preprocessing(image_path):
    """Apply multiple preprocessing techniques for better OCR accuracy based on receipt type"""
    try:
        # First, classify the receipt to determine the best preprocessing approach
        classification = classify_receipt(image_path)
        receipt_type = classification.get('receipt_type', 'unknown')
        source_type = classification.get('source_type', 'unknown')
        
        logging.info(f"Applying preprocessing for receipt type: {receipt_type}, source type: {source_type}")
        
        # Apply specialized preprocessing based on receipt type
        if receipt_type == 'walmart':
            return preprocess_walmart_receipt(image_path)
        elif receipt_type == 'thrift_store' or receipt_type == 'goodwill' or receipt_type == 'salvation_army':
            return preprocess_thrift_store_receipt(image_path)
        else:
            # If receipt type is unknown, use source type
            if source_type == 'screenshot':
                return preprocess_screenshot_receipt(image_path)
            elif source_type == 'photo':
                return preprocess_photo_receipt(image_path)
            else:
                # Fall back to generic preprocessing
                return apply_generic_preprocessing(image_path)
    except Exception as e:
        logging.error(f"Error in type-specific preprocessing: {str(e)}")
        # Fall back to generic preprocessing
        return apply_generic_preprocessing(image_path)

def apply_generic_preprocessing(image_path):
    """Apply generic preprocessing steps for receipts"""
    try:
        # Create a chain of preprocessing steps
        # 1. Start with grayscale
        grayscale_path = preprocess_grayscale(image_path)
        
        # 2. Apply denoising to remove noise
        denoised_path = preprocess_denoise(grayscale_path)
        
        # 3. Enhance contrast
        contrast_path = preprocess_contrast_enhance(denoised_path)
        
        # 4. Apply adaptive thresholding
        threshold_path = preprocess_adaptive_threshold(contrast_path)
        
        # 5. Sharpen the image
        sharpened_path = preprocess_sharpen(threshold_path)
        
        # Return all processed versions for OCR to try
        return {
            'original': image_path,
            'grayscale': grayscale_path,
            'denoised': denoised_path,
            'contrast': contrast_path,
            'threshold': threshold_path,
            'sharpened': sharpened_path,
            'processed': sharpened_path  # Best version for OCR
        }
    except Exception as e:
        logging.error(f"Error in generic preprocessing: {str(e)}")
        return {
            'original': image_path,
            'processed': image_path  # Fall back to original if preprocessing fails
        }
