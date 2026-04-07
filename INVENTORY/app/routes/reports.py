from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.inventory import Item, Listing, SaleTransaction, SalesPlatform
from datetime import datetime, timedelta
from sqlalchemy import func, extract, and_

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    """Reports dashboard"""
    from app.models.inventory import SaleTransaction
    from sqlalchemy import func, extract
    from datetime import datetime
    
    # Calculate total sales and profit
    total_sales = db.session.query(func.sum(SaleTransaction.final_sale_price)).scalar() or 0
    
    total_profit = 0
    for transaction in SaleTransaction.query.all():
        total_profit += transaction.calculate_profit()
    
    # Calculate profit margin
    profit_margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
    
    # Get monthly sales data for the current year
    current_year = datetime.utcnow().year
    monthly_sales = [0] * 12
    monthly_profit = [0] * 12
    
    for month in range(1, 13):
        # Get transactions for this month
        transactions = SaleTransaction.query.filter(
            extract('year', SaleTransaction.date_sold) == current_year,
            extract('month', SaleTransaction.date_sold) == month
        ).all()
        
        # Calculate totals
        monthly_sales[month - 1] = sum(t.final_sale_price for t in transactions)
        monthly_profit[month - 1] = sum(t.calculate_profit() for t in transactions)
    
    return render_template('reports/index.html',
                          total_sales="{:.2f}".format(total_sales),
                          total_profit="{:.2f}".format(total_profit),
                          profit_margin="{:.2f}".format(profit_margin),
                          monthly_sales=monthly_sales,
                          monthly_profit=monthly_profit)

@reports_bp.route('/profit_loss')
@login_required
def profit_loss():
    """Profit and loss report"""
    # Get date range from query parameters (default to last 30 days)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            start_date = datetime.utcnow() - timedelta(days=30)
    else:
        start_date = datetime.utcnow() - timedelta(days=30)
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            end_date = datetime.utcnow()
    else:
        end_date = datetime.utcnow()

    # Query transactions in date range
    transactions = SaleTransaction.query.filter(
        SaleTransaction.date_sold >= start_date,
        SaleTransaction.date_sold <= end_date
    ).all()
    
    # Calculate totals
    total_revenue = sum(t.final_sale_price for t in transactions)
    total_cost = sum(t.listing.item.cost_price for t in transactions)
    total_tax = sum(t.tax_amount for t in transactions)
    total_platform_fees = sum(t.platform_fee for t in transactions)
    total_shipping = sum(t.shipping_cost for t in transactions)
    total_other_fees = sum(t.other_fees for t in transactions)

    total_expenses = total_cost + total_tax + total_platform_fees + total_shipping + total_other_fees
    net_profit = total_revenue - total_expenses

    # Calculate profit margin
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

    return render_template('reports/profit_loss.html',
                          start_date=start_date,
                          end_date=end_date,
                          transactions=transactions,
                          total_revenue=total_revenue,
                          total_cost=total_cost,
                          total_tax=total_tax,
                          total_platform_fees=total_platform_fees,
                          total_shipping=total_shipping,
                          total_other_fees=total_other_fees,
                          total_expenses=total_expenses,
                          net_profit=net_profit,
                          profit_margin=profit_margin)

@reports_bp.route('/inventory_aging')
@login_required
def inventory_aging():
    """Inventory aging report"""
    # Get all items with their time in stock
    items = Item.query.all()
    
    # Group items by age
    age_groups = {
        '0-30 days': [],
        '31-60 days': [],
        '61-90 days': [],
        '91-180 days': [],
        '181+ days': []
    }
    
    for item in items:
        days_in_stock = item.time_in_stock()
        
        if days_in_stock <= 30:
            age_groups['0-30 days'].append(item)
        elif days_in_stock <= 60:
            age_groups['31-60 days'].append(item)
        elif days_in_stock <= 90:
            age_groups['61-90 days'].append(item)
        elif days_in_stock <= 180:
            age_groups['91-180 days'].append(item)
        else:
            age_groups['181+ days'].append(item)
    
    # Calculate total inventory value by age group
    age_group_values = {}
    for group, items_list in age_groups.items():
        age_group_values[group] = sum(item.cost_price * item.current_quantity() for item in items_list)
    
    return render_template('reports/inventory_aging.html',
                          age_groups=age_groups,
                          age_group_values=age_group_values)

@reports_bp.route('/sales_by_platform')
@login_required
def sales_by_platform():
    """Sales by platform report"""
    # Get date range from query parameters (default to last 30 days)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            start_date = datetime.utcnow() - timedelta(days=30)
    else:
        start_date = datetime.utcnow() - timedelta(days=30)
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            end_date = datetime.utcnow()
    else:
        end_date = datetime.utcnow()
    
    # Get all platforms
    platforms = SalesPlatform.query.all()
    
    # Calculate sales and profit by platform
    platform_stats = {}
    
    for platform in platforms:
        # Get transactions for this platform in date range
        transactions = SaleTransaction.query.join(Listing).filter(
            Listing.platform_id == platform.id,
            SaleTransaction.date_sold >= start_date,
            SaleTransaction.date_sold <= end_date
        ).all()
        
        # Calculate totals
        total_sales = sum(t.final_sale_price for t in transactions)
        total_profit = sum(t.calculate_profit() for t in transactions)
        transaction_count = len(transactions)
        
        platform_stats[platform.id] = {
            'name': platform.name,
            'total_sales': total_sales,
            'total_profit': total_profit,
            'transaction_count': transaction_count,
            'avg_sale': total_sales / transaction_count if transaction_count > 0 else 0,
            'profit_margin': (total_profit / total_sales * 100) if total_sales > 0 else 0
        }
    
    return render_template('reports/sales_by_platform.html',
                          start_date=start_date,
                          end_date=end_date,
                          platforms=platforms,
                          platform_stats=platform_stats)

@reports_bp.route('/monthly_sales')
@login_required
def monthly_sales():
    """Monthly sales report"""
    # Get year from query parameters (default to current year)
    current_year = datetime.utcnow().year
    try:
        year = int(request.args.get('year', current_year))
    except (ValueError, TypeError):
        year = current_year
    # Constrain year to a reasonable range
    year = max(2000, min(year, current_year + 1))
    
    # Query monthly sales for the year
    monthly_data = []
    
    for month in range(1, 13):
        # Get transactions for this month
        transactions = SaleTransaction.query.filter(
            extract('year', SaleTransaction.date_sold) == year,
            extract('month', SaleTransaction.date_sold) == month
        ).all()
        
        # Calculate totals
        total_sales = sum(t.final_sale_price for t in transactions)
        total_profit = sum(t.calculate_profit() for t in transactions)
        transaction_count = len(transactions)
        
        monthly_data.append({
            'month': month,
            'month_name': datetime(year, month, 1).strftime('%B'),
            'total_sales': total_sales,
            'total_profit': total_profit,
            'transaction_count': transaction_count
        })
    
    # Calculate year totals
    year_total_sales = sum(month['total_sales'] for month in monthly_data)
    year_total_profit = sum(month['total_profit'] for month in monthly_data)
    year_transaction_count = sum(month['transaction_count'] for month in monthly_data)
    
    return render_template('reports/monthly_sales.html',
                          year=year,
                          monthly_data=monthly_data,
                          year_total_sales=year_total_sales,
                          year_total_profit=year_total_profit,
                          year_transaction_count=year_transaction_count)

@reports_bp.route('/api/chart_data')
@login_required
def chart_data():
    """API endpoint for chart data"""
    chart_type = request.args.get('type')
    
    if chart_type == 'monthly_sales':
        # Get year from query parameters (default to current year)
        current_yr = datetime.utcnow().year
        try:
            year = int(request.args.get('year', current_yr))
        except (ValueError, TypeError):
            year = current_yr
        year = max(2000, min(year, current_yr + 1))
        
        # Query monthly sales for the year
        monthly_data = []
        
        for month in range(1, 13):
            # Get transactions for this month
            transactions = SaleTransaction.query.filter(
                extract('year', SaleTransaction.date_sold) == year,
                extract('month', SaleTransaction.date_sold) == month
            ).all()
            
            # Calculate totals
            total_sales = sum(t.final_sale_price for t in transactions)
            total_profit = sum(t.calculate_profit() for t in transactions)
            
            monthly_data.append({
                'month': datetime(year, month, 1).strftime('%B'),
                'sales': total_sales,
                'profit': total_profit
            })
        
        return jsonify(monthly_data)
    
    elif chart_type == 'platform_sales':
        # Get all platforms
        platforms = SalesPlatform.query.all()
        
        # Calculate sales by platform
        platform_data = []
        
        for platform in platforms:
            # Get transactions for this platform
            transactions = SaleTransaction.query.join(Listing).filter(
                Listing.platform_id == platform.id
            ).all()
            
            # Calculate total sales
            total_sales = sum(t.final_sale_price for t in transactions)
            
            platform_data.append({
                'platform': platform.name,
                'sales': total_sales
            })
        
        return jsonify(platform_data)
    
    elif chart_type == 'inventory_aging':
        # Get all items with their time in stock
        items = Item.query.all()
        
        # Group items by age
        age_groups = {
            '0-30 days': 0,
            '31-60 days': 0,
            '61-90 days': 0,
            '91-180 days': 0,
            '181+ days': 0
        }
        
        for item in items:
            days_in_stock = item.time_in_stock()
            quantity = item.current_quantity()
            
            if days_in_stock <= 30:
                age_groups['0-30 days'] += quantity
            elif days_in_stock <= 60:
                age_groups['31-60 days'] += quantity
            elif days_in_stock <= 90:
                age_groups['61-90 days'] += quantity
            elif days_in_stock <= 180:
                age_groups['91-180 days'] += quantity
            else:
                age_groups['181+ days'] += quantity
        
        # Format data for chart
        aging_data = [
            {'age_group': group, 'count': count}
            for group, count in age_groups.items()
        ]
        
        return jsonify(aging_data)
    
    return jsonify({'error': 'Invalid chart type'})
