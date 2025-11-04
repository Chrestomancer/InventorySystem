from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from app import db
from app.models.inventory import Item, Listing, SaleTransaction, SalesPlatform
from datetime import datetime

sales_bp = Blueprint('sales', __name__)

# Listing routes
@sales_bp.route('/')
@login_required
def index():
    """List all listings"""
    query = Listing.query.join(Item).join(SalesPlatform)

    platform_id = request.args.get('platform', type=int)
    status = request.args.get('status', type=str)
    search_term = (request.args.get('search') or '').strip()
    price_min_raw = request.args.get('price_min', '').strip()
    price_max_raw = request.args.get('price_max', '').strip()

    price_min = None
    price_max = None

    try:
        if price_min_raw:
            price_min = float(price_min_raw)
    except ValueError:
        price_min_raw = ''

    try:
        if price_max_raw:
            price_max = float(price_max_raw)
    except ValueError:
        price_max_raw = ''

    if platform_id:
        query = query.filter(Listing.platform_id == platform_id)

    if status:
        query = query.filter(Listing.status == status)

    if price_min is not None:
        query = query.filter(Listing.listing_price >= price_min)

    if price_max is not None:
        query = query.filter(Listing.listing_price <= price_max)

    if search_term:
        like_term = f"%{search_term}%"
        query = query.filter(or_(Item.name.ilike(like_term), Item.sku.ilike(like_term)))

    listings = query.order_by(Listing.date_listed.desc()).all()
    platforms = SalesPlatform.query.order_by(SalesPlatform.name).all()
    status_rows = db.session.query(Listing.status).distinct().order_by(Listing.status).all()
    statuses = [row[0] for row in status_rows if row[0]]

    filters = {
        'platform': platform_id,
        'status': status,
        'search': search_term,
        'price_min': price_min_raw,
        'price_max': price_max_raw
    }

    return render_template('sales/index.html',
                           listings=listings,
                           platforms=platforms,
                           statuses=statuses,
                           filters=filters)

@sales_bp.route('/listing/<int:listing_id>')
@login_required
def view_listing(listing_id):
    """View a specific listing"""
    listing = Listing.query.get_or_404(listing_id)
    transactions = listing.transactions.all()
    return render_template('sales/view_listing.html', listing=listing, transactions=transactions)

@sales_bp.route('/item/<int:item_id>/add_listing', methods=['GET', 'POST'])
@login_required
def add_listing(item_id):
    """Add a new listing for an item"""
    item = Item.query.get_or_404(item_id)
    platforms = SalesPlatform.query.all()
    
    if request.method == 'POST':
        platform_id = int(request.form.get('platform_id'))
        listing_url = request.form.get('listing_url')
        listing_price = float(request.form.get('listing_price', 0))
        
        # Create new listing
        listing = Listing(
            item_id=item.id,
            platform_id=platform_id,
            listing_url=listing_url,
            listing_price=listing_price,
            status='active',
            date_listed=datetime.utcnow()
        )
        
        db.session.add(listing)
        db.session.commit()
        
        flash('Listing added successfully', 'success')
        return redirect(url_for('inventory.view_item', item_id=item.id))
    
    return render_template('sales/add_listing.html', item=item, platforms=platforms)

@sales_bp.route('/listing/<int:listing_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_listing(listing_id):
    """Edit a listing"""
    listing = Listing.query.get_or_404(listing_id)
    platforms = SalesPlatform.query.all()
    
    if request.method == 'POST':
        platform_id = int(request.form.get('platform_id'))
        listing_url = request.form.get('listing_url')
        listing_price = float(request.form.get('listing_price', 0))
        status = request.form.get('status')
        
        # Update listing
        listing.platform_id = platform_id
        listing.listing_url = listing_url
        listing.listing_price = listing_price
        listing.status = status
        
        # If status changed to sold, update date_sold
        if status == 'sold' and not listing.date_sold:
            listing.date_sold = datetime.utcnow()
        elif status != 'sold':
            listing.date_sold = None
        
        db.session.commit()
        
        flash('Listing updated successfully', 'success')
        return redirect(url_for('sales.view_listing', listing_id=listing.id))
    
    return render_template('sales/edit_listing.html', listing=listing, platforms=platforms)

@sales_bp.route('/listing/<int:listing_id>/delete', methods=['POST'])
@login_required
def delete_listing(listing_id):
    """Delete a listing"""
    listing = Listing.query.get_or_404(listing_id)
    item_id = listing.item_id
    
    # Check if listing has any transactions
    if listing.transactions.count() > 0:
        flash('Cannot delete listing with transactions', 'danger')
        return redirect(url_for('sales.view_listing', listing_id=listing.id))
    
    db.session.delete(listing)
    db.session.commit()
    
    flash('Listing deleted successfully', 'success')
    return redirect(url_for('inventory.view_item', item_id=item_id))

# Transaction routes
@sales_bp.route('/listing/<int:listing_id>/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction(listing_id):
    """Add a new transaction for a listing"""
    listing = Listing.query.get_or_404(listing_id)
    
    if request.method == 'POST':
        final_sale_price = float(request.form.get('final_sale_price', 0))
        tax_amount = float(request.form.get('tax_amount', 0))
        platform_fee = float(request.form.get('platform_fee', 0))
        shipping_cost = float(request.form.get('shipping_cost', 0))
        other_fees = float(request.form.get('other_fees', 0))
        
        # Create new transaction
        transaction = SaleTransaction(
            listing_id=listing.id,
            final_sale_price=final_sale_price,
            tax_amount=tax_amount,
            platform_fee=platform_fee,
            shipping_cost=shipping_cost,
            other_fees=other_fees,
            date_sold=datetime.utcnow()
        )
        
        # Update listing status to sold
        listing.status = 'sold'
        listing.date_sold = datetime.utcnow()
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Transaction added successfully', 'success')
        return redirect(url_for('sales.view_listing', listing_id=listing.id))
    
    return render_template('sales/add_transaction.html', listing=listing)

@sales_bp.route('/transaction/<int:transaction_id>')
@login_required
def view_transaction(transaction_id):
    """View a specific transaction"""
    transaction = SaleTransaction.query.get_or_404(transaction_id)
    profit = transaction.calculate_profit()
    profit_margin = transaction.calculate_profit_margin()
    
    return render_template('sales/view_transaction.html', 
                          transaction=transaction, 
                          profit=profit, 
                          profit_margin=profit_margin)

@sales_bp.route('/transaction/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    """Edit a transaction"""
    transaction = SaleTransaction.query.get_or_404(transaction_id)
    
    if request.method == 'POST':
        final_sale_price = float(request.form.get('final_sale_price', 0))
        tax_amount = float(request.form.get('tax_amount', 0))
        platform_fee = float(request.form.get('platform_fee', 0))
        shipping_cost = float(request.form.get('shipping_cost', 0))
        other_fees = float(request.form.get('other_fees', 0))
        
        # Update transaction
        transaction.final_sale_price = final_sale_price
        transaction.tax_amount = tax_amount
        transaction.platform_fee = platform_fee
        transaction.shipping_cost = shipping_cost
        transaction.other_fees = other_fees
        
        db.session.commit()
        
        flash('Transaction updated successfully', 'success')
        return redirect(url_for('sales.view_transaction', transaction_id=transaction.id))
    
    return render_template('sales/edit_transaction.html', transaction=transaction)

@sales_bp.route('/transaction/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    """Delete a transaction"""
    transaction = SaleTransaction.query.get_or_404(transaction_id)
    listing_id = transaction.listing_id
    
    # Update listing status back to active if this was the only transaction
    listing = transaction.listing
    if listing.transactions.count() == 1:
        listing.status = 'active'
        listing.date_sold = None
    
    db.session.delete(transaction)
    db.session.commit()
    
    flash('Transaction deleted successfully', 'success')
    return redirect(url_for('sales.view_listing', listing_id=listing_id))

# Sales Dashboard
@sales_bp.route('/dashboard')
@login_required
def dashboard():
    """Sales dashboard with summary statistics"""
    # Get recent transactions
    recent_transactions = SaleTransaction.query.order_by(
        SaleTransaction.date_sold.desc()
    ).limit(10).all()
    
    # Calculate total sales
    total_sales = db.session.query(
        db.func.sum(SaleTransaction.final_sale_price)
    ).scalar() or 0
    
    # Calculate total profit
    total_profit = 0
    for transaction in SaleTransaction.query.all():
        total_profit += transaction.calculate_profit()
    
    # Get active listings count
    active_listings = Listing.query.filter_by(status='active').count()
    
    # Get sold listings count
    sold_listings = Listing.query.filter_by(status='sold').count()
    
    return render_template('sales/dashboard.html',
                          recent_transactions=recent_transactions,
                          total_sales=total_sales,
                          total_profit=total_profit,
                          active_listings=active_listings,
                          sold_listings=sold_listings)
