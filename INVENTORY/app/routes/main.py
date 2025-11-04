from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from app import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page route"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard route - requires login"""
    from app.models.inventory import Item, Listing, SaleTransaction
    from sqlalchemy import desc
    from datetime import datetime

    items = Item.query.all()

    # Get inventory summary
    total_items = len(items)

    # Define low stock threshold (e.g., items with quantity < 5)
    low_stock_threshold = 5
    low_stock_items = []

    # Aggregate inventory metrics
    total_quantity = 0
    inventory_value = 0
    for item in items:
        quantity_on_hand = item.current_quantity()
        total_quantity += quantity_on_hand
        inventory_value += item.cost_price * quantity_on_hand

        if quantity_on_hand < low_stock_threshold:
            low_stock_items.append({
                'item': item,
                'quantity': quantity_on_hand
            })

    low_stock = len(low_stock_items)

    # Get sales summary
    active_listings = Listing.query.filter_by(status='active').count()
    sold_items = Listing.query.filter_by(status='sold').count()

    # Calculate total sales and profit
    total_sales_result = db.session.execute('SELECT SUM(final_sale_price) FROM sale_transactions')
    total_sales = total_sales_result.scalar() or 0

    total_profit = 0
    for transaction in SaleTransaction.query.all():
        total_profit += transaction.calculate_profit()

    # Get recently added items (last 5)
    recent_items = Item.query.order_by(desc(Item.created_at)).limit(5).all()

    # Get recent sales (last 5)
    recent_sales = SaleTransaction.query.order_by(desc(SaleTransaction.date_sold)).limit(5).all()

    # Determine available years for sales data
    date_rows = SaleTransaction.query\
        .with_entities(SaleTransaction.date_sold)\
        .filter(SaleTransaction.date_sold.isnot(None))\
        .all()
    available_years = sorted({row[0].year for row in date_rows if row[0]})

    current_year = datetime.utcnow().year
    if not available_years:
        available_years = [current_year]

    selected_year = request.args.get('year', type=int)
    if selected_year not in available_years:
        selected_year = available_years[-1] if available_years else current_year

    monthly_sales = [0] * 12
    monthly_profit = [0] * 12

    for month in range(1, 13):
        start_date = datetime(selected_year, month, 1)
        if month == 12:
            next_month_start = datetime(selected_year + 1, 1, 1)
        else:
            next_month_start = datetime(selected_year, month + 1, 1)

        transactions = SaleTransaction.query.filter(
            SaleTransaction.date_sold >= start_date,
            SaleTransaction.date_sold < next_month_start
        ).all()

        monthly_sales[month - 1] = sum(t.final_sale_price for t in transactions)
        monthly_profit[month - 1] = sum(t.calculate_profit() for t in transactions)

    month_labels = [datetime(2000, month, 1).strftime('%b') for month in range(1, 13)]

    return render_template('dashboard.html',
                          total_items=total_items,
                          total_quantity=total_quantity,
                          low_stock=low_stock,
                          low_stock_items=low_stock_items,
                          low_stock_threshold=low_stock_threshold,
                          inventory_value="{:.2f}".format(inventory_value),
                          active_listings=active_listings,
                          sold_items=sold_items,
                          total_sales="{:.2f}".format(total_sales),
                          total_profit="{:.2f}".format(total_profit),
                          recent_items=recent_items,
                          recent_sales=recent_sales,
                          monthly_sales=monthly_sales,
                          monthly_profit=monthly_profit,
                          available_years=available_years,
                          selected_year=selected_year,
                          month_labels=month_labels)

@main_bp.route('/about')
def about():
    """About page route"""
    return render_template('about.html')
