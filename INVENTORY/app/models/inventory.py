from app import db
from datetime import datetime

class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(50), unique=True, index=True)
    condition = db.Column(db.String(50))  # new, used, refurbished, etc.
    cost_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    inventory_records = db.relationship('InventoryRecord', backref='item', lazy='dynamic')
    listings = db.relationship('Listing', backref='item', lazy='dynamic')

    def __repr__(self):
        return f'<Item {self.name} (SKU: {self.sku})>'

    def current_quantity(self):
        """Calculate the current quantity across all inventory records"""
        return sum(record.quantity for record in self.inventory_records)

    def time_in_stock(self):
        """Calculate the time in stock (in days)"""
        if not self.created_at:
            return 0
        return (datetime.utcnow() - self.created_at).days

class InventoryRecord(db.Model):
    __tablename__ = 'inventory_records'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    location = db.Column(db.String(100))  # warehouse, shelf, etc.
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<InventoryRecord for Item {self.item_id}: {self.quantity} at {self.location}>'

class SalesPlatform(db.Model):
    __tablename__ = 'sales_platforms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    url = db.Column(db.String(200))
    fee_percentage = db.Column(db.Float, default=0)  # Platform fee as a percentage

    # Relationships
    listings = db.relationship('Listing', backref='platform', lazy='dynamic')

    def __repr__(self):
        return f'<SalesPlatform {self.name}>'

class Listing(db.Model):
    __tablename__ = 'listings'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    platform_id = db.Column(db.Integer, db.ForeignKey('sales_platforms.id'), nullable=False)
    listing_url = db.Column(db.String(255))
    listing_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, sold, expired, etc.
    date_listed = db.Column(db.DateTime, default=datetime.utcnow)
    date_sold = db.Column(db.DateTime)

    # Relationships
    transactions = db.relationship('SaleTransaction', backref='listing', lazy='dynamic')

    def __repr__(self):
        return f'<Listing for Item {self.item_id} on Platform {self.platform_id}>'

    def time_listed(self):
        """Calculate the time listed (in days)"""
        if not self.date_listed:
            return 0
        end_date = self.date_sold if self.date_sold else datetime.utcnow()
        return (end_date - self.date_listed).days

class SaleTransaction(db.Model):
    __tablename__ = 'sale_transactions'

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('listings.id'), nullable=False)
    final_sale_price = db.Column(db.Float, nullable=False)
    tax_amount = db.Column(db.Float, default=0)
    platform_fee = db.Column(db.Float, default=0)
    shipping_cost = db.Column(db.Float, default=0)
    other_fees = db.Column(db.Float, default=0)
    date_sold = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SaleTransaction for Listing {self.listing_id}: ${self.final_sale_price}>'

    def calculate_profit(self):
        """Calculate profit for this transaction"""
        # Get the item cost from the related listing and item
        item_cost = self.listing.item.cost_price

        # Calculate total costs
        total_cost = item_cost + self.tax_amount + self.platform_fee + self.shipping_cost + self.other_fees

        # Calculate profit
        profit = self.final_sale_price - total_cost

        return profit

    def calculate_profit_margin(self):
        """Calculate profit margin as a percentage"""
        profit = self.calculate_profit()

        if self.final_sale_price == 0:
            return 0

        profit_margin = (profit / self.final_sale_price) * 100
        return profit_margin
