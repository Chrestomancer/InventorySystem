from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session, jsonify, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.inventory import Item, InventoryRecord, SalesPlatform, Listing, SaleTransaction
from app.utils.document_processing import save_uploaded_file, process_document, map_to_inventory_system
import os
import json
from datetime import datetime

documents_bp = Blueprint('documents', __name__)

@documents_bp.route('/')
@login_required
def index():
    """Document scanning main page"""
    return render_template('documents/upload.html')

@documents_bp.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle document upload and processing"""
    if 'document' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('documents.index'))

    file = request.files['document']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('documents.index'))

    # Validate file extension
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.pdf', '.html', '.htm'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        flash('Unsupported file type. Please upload an image, PDF, or HTML file.', 'danger')
        return redirect(url_for('documents.index'))

    # Create upload folder if it doesn't exist
    upload_folder = os.path.join(current_app.root_path, '..', 'uploads', 'documents')
    os.makedirs(upload_folder, exist_ok=True)

    try:
        # Save the uploaded file
        file_path = save_uploaded_file(file, upload_folder)

        # Process the document (this might take some time)
        flash('Processing document, this may take a moment...', 'info')
        results = process_document(file_path)

        if 'error' in results:
            flash(f'Error processing document: {results["error"]}', 'danger')
            return redirect(url_for('documents.index'))

        # Store the extracted data in session for review
        session['document_results'] = json.dumps(results, default=str)
        session['document_path'] = file_path

        return redirect(url_for('documents.review'))

    except Exception as e:
        flash(f'Error processing document: {str(e)}', 'danger')
        return redirect(url_for('documents.index'))

@documents_bp.route('/review', methods=['GET', 'POST'])
@login_required
def review():
    """Review and confirm extracted data"""
    # Get data from session
    results_json = session.get('document_results', '{}')
    document_path = session.get('document_path', '')

    try:
        results = json.loads(results_json)
    except json.JSONDecodeError:
        results = {}

    if not results or 'extracted_data' not in results:
        flash('No document data to review', 'danger')
        return redirect(url_for('documents.index'))

    # Extract the data
    extracted_data = results.get('extracted_data', {})
    confidence_scores = results.get('confidence_scores', {})
    receipt_classification = results.get('receipt_classification', None)

    # Get all platforms for the dropdown
    platforms = SalesPlatform.query.all()

    # Get active listings for transaction mode
    active_listings = Listing.query.filter_by(status='active').all()

    if request.method == 'POST':
        # User has confirmed the data, process it
        try:
            # Get form data
            action = request.form.get('action', 'inventory')
            redirect_target = None

            if action == 'inventory':
                # Process as inventory items
                process_as_inventory(request.form, extracted_data)
                flash('Items imported successfully to inventory', 'success')
                redirect_target = url_for('inventory.index')

            elif action == 'transaction':
                # Process as a sales transaction
                process_as_transaction(request.form)
                flash('Transaction recorded successfully', 'success')
                redirect_target = url_for('sales.index')
            else:
                flash('Invalid action specified for document processing', 'danger')

            if redirect_target:
                # Clear session data before redirecting
                session.pop('document_results', None)
                session.pop('document_path', None)
                return redirect(redirect_target)

        except Exception as e:
            db.session.rollback()
            flash(f'Error importing data: {str(e)}', 'danger')

    # For GET request, display the review form
    return render_template('documents/review.html', 
                          extracted_data=extracted_data,
                          confidence_scores=confidence_scores,
                          document_path=document_path,
                          platforms=platforms,
                          active_listings=active_listings,
                          ocr_text=results.get('ocr_results', {}).get('combined_text', ''),
                          receipt_classification=receipt_classification)

def process_as_inventory(form_data, extracted_data):
    """Process the document data as inventory items"""
    vendor_name = form_data.get('vendor_name')
    date_str = form_data.get('date')

    # Check if we need to create a new platform
    platform_id = form_data.get('platform_name')
    if platform_id == 'new':
        # Create new platform
        new_platform_name = form_data.get('new_platform_name')
        platform_url = form_data.get('platform_url')
        fee_percentage = float(form_data.get('fee_percentage', 0))

        platform = SalesPlatform(
            name=new_platform_name,
            url=platform_url,
            fee_percentage=fee_percentage
        )
        db.session.add(platform)
        db.session.flush()  # Get the platform ID
        platform_id = platform.id

    # Process items
    items_count = int(form_data.get('items_count', 0))

    for i in range(items_count):
        item_name = form_data.get(f'item_name_{i}')
        item_sku = form_data.get(f'item_sku_{i}')
        item_condition = form_data.get(f'item_condition_{i}')
        item_quantity = int(form_data.get(f'item_quantity_{i}', 1))
        item_price = float(form_data.get(f'item_price_{i}', 0))

        if item_name and item_price > 0:
            # Check if item exists by SKU
            item = None
            if item_sku:
                item = Item.query.filter_by(sku=item_sku).first()

            # If not found by SKU, check by name
            if not item:
                item = Item.query.filter_by(name=item_name).first()

            if not item:
                # Create new item
                item = Item(
                    name=item_name,
                    description=f"Added from receipt: {vendor_name}",
                    sku=item_sku,
                    condition=item_condition,
                    cost_price=item_price
                )
                db.session.add(item)
                db.session.flush()  # Get the item ID

            # Add inventory record
            record = InventoryRecord(
                item_id=item.id,
                quantity=item_quantity,
                location=f"Receipt import: {date_str or datetime.now().strftime('%Y-%m-%d')}"
            )
            db.session.add(record)

    db.session.commit()

def process_as_transaction(form_data):
    """Process the document data as a sales transaction"""
    try:
        listing_id = int(form_data.get('listing_id'))
        final_sale_price = float(form_data.get('final_sale_price', 0))
        tax_amount = float(form_data.get('tax_amount', 0))
        platform_fee = float(form_data.get('platform_fee', 0))
        shipping_cost = float(form_data.get('shipping_cost', 0))
        other_fees = float(form_data.get('other_fees', 0))
    except (ValueError, TypeError) as e:
        raise ValueError(f'Invalid numeric value in transaction data: {e}')

    # Create new transaction
    transaction = SaleTransaction(
        listing_id=listing_id,
        final_sale_price=final_sale_price,
        tax_amount=tax_amount,
        platform_fee=platform_fee,
        shipping_cost=shipping_cost,
        other_fees=other_fees,
        date_sold=datetime.utcnow()
    )

    # Update listing status to sold
    listing = Listing.query.get(listing_id)
    listing.status = 'sold'
    listing.date_sold = datetime.utcnow()

    db.session.add(transaction)
    db.session.commit()

@documents_bp.route('/image/<path:filename>')
@login_required
def get_image(filename):
    """Serve the uploaded image"""
    # Restrict to the uploads directory to prevent path traversal
    upload_folder = os.path.realpath(os.path.join(current_app.root_path, '..', 'uploads', 'documents'))
    safe_filename = os.path.basename(filename)
    return send_from_directory(upload_folder, safe_filename)
