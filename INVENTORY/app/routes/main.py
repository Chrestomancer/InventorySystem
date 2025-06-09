from flask import Blueprint, render_template, redirect, url_for
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
    from sqlalchemy import func, desc
    from datetime import datetime, timedelta

    # Get inventory summary
    total_items = Item.query.count()

    # Calculate total quantity across all inventory records
    total_quantity = sum(item.current_quantity() for item in Item.query.all())

    # Define low stock threshold (e.g., items with quantity < 5)
    low_stock_threshold = 5
    low_stock = 0
    for item in Item.query.all():
        if item.current_quantity() < low_stock_threshold:
            low_stock += 1

    # Calculate total inventory value
    inventory_value = 0
    for item in Item.query.all():
        inventory_value += item.cost_price * item.current_quantity()

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

    # Get monthly sales data for the current year
    current_year = datetime.utcnow().year
    monthly_sales = [0] * 12
    monthly_profit = [0] * 12

    for month in range(1, 13):
        # Get transactions for this month
        start_date = datetime(current_year, month, 1)
        if month == 12:
            end_date = datetime(current_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(current_year, month + 1, 1) - timedelta(days=1)

        transactions = SaleTransaction.query.filter(
            SaleTransaction.date_sold >= start_date,
            SaleTransaction.date_sold <= end_date
        ).all()

        # Calculate totals
        monthly_sales[month - 1] = sum(t.final_sale_price for t in transactions)
        monthly_profit[month - 1] = sum(t.calculate_profit() for t in transactions)

    return render_template('dashboard.html',
                          total_items=total_items,
                          total_quantity=total_quantity,
                          low_stock=low_stock,
                          inventory_value="{:.2f}".format(inventory_value),
                          active_listings=active_listings,
                          sold_items=sold_items,
                          total_sales="{:.2f}".format(total_sales),
                          total_profit="{:.2f}".format(total_profit),
                          recent_items=recent_items,
                          recent_sales=recent_sales,
                          monthly_sales=monthly_sales,
                          monthly_profit=monthly_profit)

@main_bp.route('/about')
def about():
    """About page route"""
    return render_template('about.html')
