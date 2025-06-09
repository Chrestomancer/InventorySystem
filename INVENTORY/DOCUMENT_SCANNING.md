# Document Scanning Feature

This feature allows you to scan receipts, invoices, and other documents to extract information and add it to your inventory system.

## Features

- **Receipt Type Classification**: Automatically identifies the type of receipt (e.g., Walmart, thrift store) and source type (e.g., photo, screenshot)
- **Type-Specific Preprocessing**: Applies specialized image preprocessing techniques based on receipt type
- **Optimized Vision Prompts**: Uses receipt type-specific prompts for the vision model to improve extraction accuracy
- **Multiple Preprocessing Approaches**: Applies different image preprocessing techniques to improve OCR accuracy
- **Multi-Engine OCR**: Uses OCR engines to improve text extraction
- **Rule-Based Validation**: Applies domain-specific validation rules to catch common errors
- **Confidence Scoring**: Calculates confidence scores for extracted fields to help identify potentially problematic data
- **User Review Interface**: Allows users to review and edit extracted data before adding it to the system

## Supported Document Types

- Images (JPG, PNG, TIFF)
- PDFs
- HTML/XML (e.g., eBay invoice downloads)

## Supported Receipt Types

- **Retail Receipts**: Walmart, Target, Costco, and other retail stores
- **Thrift Store Receipts**: Goodwill, Salvation Army, and other thrift stores
- **Online Marketplace Receipts**: Amazon, eBay, Etsy, and other online platforms
- **Restaurant Receipts**: Food and beverage establishments

## Installation

### Dependencies

The document scanning feature requires the following dependencies:

```
easyocr==1.7.0
opencv-python==4.7.0.72
pdf2image==1.16.3
pdfplumber==0.9.0
beautifulsoup4==4.12.2
ollama==0.1.20
```

These dependencies are included in the `requirements.txt` file. You can install them using pip:

```
pip install -r requirements.txt
```

### Additional System Dependencies

Some dependencies require additional system packages:

- **pdf2image** requires Poppler:
  - Windows: Download and install from https://github.com/oschwartz10612/poppler-windows/releases
  - macOS: `brew install poppler`
  - Linux: `apt-get install poppler-utils`

- **Ollama** for vision model:
  - Install Ollama from https://ollama.com/
  - Pull the vision model: `ollama pull llama3.2-vision:11b`

## Usage

1. Navigate to the "Scan Documents" section in the navigation menu
2. Upload a receipt, invoice, or other document
3. The system will:
   - Classify the receipt type and source
   - Apply type-specific preprocessing
   - Extract text using OCR
   - Process the image with the vision model using type-specific prompts
   - Combine and refine the results
4. Review the extracted information and make any necessary corrections
5. Choose whether to add the items to inventory or record a transaction
6. Submit the form to add the data to your inventory system

## Tips for Best Results

- Ensure the document is well-lit and clearly visible
- For photos, take them directly above the receipt
- Make sure text is readable and not blurry
- Include the entire receipt in the image
- For digital receipts, save as PDF when possible
- For Walmart receipts, ensure the store name and total are clearly visible
- For thrift store receipts, make sure item prices are clearly visible
- For online marketplace receipts, include the platform name and order number

## Troubleshooting

If you encounter issues with the document scanning feature:

1. Check that all dependencies are installed correctly
2. Ensure the document is clear and readable
3. Check if the receipt type was correctly identified (shown in the review page)
4. Try different preprocessing techniques (the system does this automatically)
5. Check the extracted text to see if the OCR is working correctly
6. If OCR is failing, try a different document format (e.g., convert image to PDF)
7. Ensure Ollama is running and the vision model is installed

## How It Works

1. **Document Upload**: The user uploads a document (image, PDF, HTML)
2. **Receipt Classification**: The system identifies the receipt type and source
3. **Type-Specific Preprocessing**: Specialized preprocessing is applied based on receipt type
4. **OCR Processing**: OCR engines extract text from the preprocessed images
5. **Vision Model Processing**: The vision model analyzes the image with type-specific prompts
6. **Data Extraction**: The system extracts structured data from the OCR text and vision model results
7. **Result Refinement**: The results are refined and cleaned up
8. **Validation**: Rule-based validation is applied to catch common errors
9. **Confidence Scoring**: Confidence scores are calculated for each extracted field
10. **User Review**: The user reviews and edits the extracted data
11. **Data Import**: The data is added to the inventory system

## Extending the Feature

The document scanning feature is designed to be extensible:

- Add new receipt types in `app/utils/receipt_classifier.py`
- Add new preprocessing techniques in `app/utils/image_preprocessing.py`
- Add new type-specific prompts in `app/utils/ollama_vision.py`
- Add new OCR engines in `app/utils/ocr_engines.py`
- Add new validation rules in `app/utils/validation_rules.py`
- Add new confidence scoring methods in `app/utils/confidence_scoring.py`
- Add new document types in `app/utils/document_processing.py`

## Receipt Classification

The system uses a combination of visual and textual features to classify receipts:

- **Visual Features**: Aspect ratio, line patterns, text regions, brightness, contrast
- **Textual Features**: Store names, format patterns, item patterns
- **Source Type**: Photo, screenshot, scan

This classification is used to apply specialized preprocessing and prompting techniques for better extraction accuracy.

## Type-Specific Processing

Different receipt types benefit from different processing approaches:

- **Walmart Receipts**: Line removal, stronger contrast enhancement, custom thresholding
- **Thrift Store Receipts**: Perspective correction, stronger denoising, binary thresholding
- **Online Marketplace Receipts**: Specialized prompts for platform-specific information
- **Photo Receipts**: Perspective correction, shadow removal, glare reduction
- **Screenshot Receipts**: Border removal, custom thresholding
