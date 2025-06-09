from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.inventory import Item, InventoryRecord, SalesPlatform
from datetime import datetime

inventory_bp = Blueprint('inventory', __name__)

# Item routes
@inventory_bp.route('/')
@login_required
def index():
    """List all inventory items"""
    items = Item.query.all()
    return render_template('inventory/index.html', items=items)

@inventory_bp.route('/item/<int:item_id>')
@login_required
def view_item(item_id):
    """View a specific inventory item"""
    item = Item.query.get_or_404(item_id)
    inventory_records = item.inventory_records.all()
    listings = item.listings.all()
    return render_template('inventory/view_item.html', item=item, 
                          inventory_records=inventory_records, listings=listings)

@inventory_bp.route('/item/add', methods=['GET', 'POST'])
@login_required
def add_item():
    """Add a new inventory item"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        sku = request.form.get('sku')
        condition = request.form.get('condition')
        cost_price = float(request.form.get('cost_price', 0))

        # Check if SKU already exists
        if sku and Item.query.filter_by(sku=sku).first():
            flash('An item with this SKU already exists', 'danger')
            return redirect(url_for('inventory.add_item'))

        # Create new item
        item = Item(
            name=name,
            description=description,
            sku=sku,
            condition=condition,
            cost_price=cost_price
        )

        db.session.add(item)
        db.session.commit()

        flash('Item added successfully', 'success')
        return redirect(url_for('inventory.view_item', item_id=item.id))

    return render_template('inventory/add_item.html')

@inventory_bp.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    """Edit an inventory item"""
    item = Item.query.get_or_404(item_id)

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        sku = request.form.get('sku')
        condition = request.form.get('condition')
        cost_price = float(request.form.get('cost_price', 0))

        # Check if SKU already exists (for another item)
        sku_exists = Item.query.filter(Item.sku == sku, Item.id != item_id).first()
        if sku and sku_exists:
            flash('An item with this SKU already exists', 'danger')
            return redirect(url_for('inventory.edit_item', item_id=item_id))

        # Update item
        item.name = name
        item.description = description
        item.sku = sku
        item.condition = condition
        item.cost_price = cost_price

        db.session.commit()

        flash('Item updated successfully', 'success')
        return redirect(url_for('inventory.view_item', item_id=item.id))

    return render_template('inventory/edit_item.html', item=item)

@inventory_bp.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    """Delete an inventory item"""
    item = Item.query.get_or_404(item_id)

    # Check if item has any listings
    if item.listings.count() > 0:
        flash('Cannot delete item with active listings', 'danger')
        return redirect(url_for('inventory.view_item', item_id=item.id))

    # Delete inventory records
    for record in item.inventory_records:
        db.session.delete(record)

    # Delete item
    db.session.delete(item)
    db.session.commit()

    flash('Item deleted successfully', 'success')
    return redirect(url_for('inventory.index'))

# Inventory Record routes
@inventory_bp.route('/item/<int:item_id>/add_record', methods=['GET', 'POST'])
@login_required
def add_inventory_record(item_id):
    """Add a new inventory record for an item"""
    item = Item.query.get_or_404(item_id)

    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 0))
        location = request.form.get('location')

        # Create new inventory record
        record = InventoryRecord(
            item_id=item.id,
            quantity=quantity,
            location=location
        )

        db.session.add(record)
        db.session.commit()

        flash('Inventory record added successfully', 'success')
        return redirect(url_for('inventory.view_item', item_id=item.id))

    return render_template('inventory/add_record.html', item=item)

@inventory_bp.route('/record/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_inventory_record(record_id):
    """Edit an inventory record"""
    record = InventoryRecord.query.get_or_404(record_id)

    if request.method == 'POST':
        quantity = int(request.form.get('quantity', 0))
        location = request.form.get('location')

        # Update record
        record.quantity = quantity
        record.location = location

        db.session.commit()

        flash('Inventory record updated successfully', 'success')
        return redirect(url_for('inventory.view_item', item_id=record.item_id))

    return render_template('inventory/edit_record.html', record=record)

@inventory_bp.route('/record/<int:record_id>/delete', methods=['POST'])
@login_required
def delete_inventory_record(record_id):
    """Delete an inventory record"""
    record = InventoryRecord.query.get_or_404(record_id)
    item_id = record.item_id

    db.session.delete(record)
    db.session.commit()

    flash('Inventory record deleted successfully', 'success')
    return redirect(url_for('inventory.view_item', item_id=item_id))

# Sales Platform routes
@inventory_bp.route('/platforms')
@login_required
def list_platforms():
    """List all sales platforms"""
    platforms = SalesPlatform.query.all()
    return render_template('inventory/platforms.html', platforms=platforms)

@inventory_bp.route('/platform/add', methods=['GET', 'POST'])
@login_required
def add_platform():
    """Add a new sales platform"""
    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
        fee_percentage = float(request.form.get('fee_percentage', 0))

        # Check if platform already exists
        if SalesPlatform.query.filter_by(name=name).first():
            flash('A platform with this name already exists', 'danger')
            return redirect(url_for('inventory.add_platform'))

        # Create new platform
        platform = SalesPlatform(
            name=name,
            url=url,
            fee_percentage=fee_percentage
        )

        db.session.add(platform)
        db.session.commit()

        flash('Sales platform added successfully', 'success')
        return redirect(url_for('inventory.list_platforms'))

    return render_template('inventory/add_platform.html')

@inventory_bp.route('/platform/<int:platform_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_platform(platform_id):
    """Edit a sales platform"""
    platform = SalesPlatform.query.get_or_404(platform_id)

    if request.method == 'POST':
        name = request.form.get('name')
        url = request.form.get('url')
        fee_percentage = float(request.form.get('fee_percentage', 0))

        # Check if platform name already exists (for another platform)
        name_exists = SalesPlatform.query.filter(
            SalesPlatform.name == name, 
            SalesPlatform.id != platform_id
        ).first()

        if name_exists:
            flash('A platform with this name already exists', 'danger')
            return redirect(url_for('inventory.edit_platform', platform_id=platform_id))

        # Update platform
        platform.name = name
        platform.url = url
        platform.fee_percentage = fee_percentage

        db.session.commit()

        flash('Sales platform updated successfully', 'success')
        return redirect(url_for('inventory.list_platforms'))

    return render_template('inventory/edit_platform.html', platform=platform)

@inventory_bp.route('/platform/<int:platform_id>/delete', methods=['POST'])
@login_required
def delete_platform(platform_id):
    """Delete a sales platform"""
    platform = SalesPlatform.query.get_or_404(platform_id)

    # Check if platform has any listings
    if platform.listings.count() > 0:
        flash('Cannot delete platform with active listings', 'danger')
        return redirect(url_for('inventory.list_platforms'))

    db.session.delete(platform)
    db.session.commit()

    flash('Sales platform deleted successfully', 'success')
    return redirect(url_for('inventory.list_platforms'))
