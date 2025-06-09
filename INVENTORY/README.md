# Inventory Management System

A comprehensive inventory management system for resellers and small business owners to track inventory, manage listings across multiple sales platforms, and analyze sales performance.

## Features

- **User Authentication**: Secure login and registration with role-based access control
- **Inventory Management**: Add, edit, and track inventory items with detailed information
- **Sales Channel Integration**: Manage listings across multiple sales platforms
- **Transaction Tracking**: Record sales with automatic profit calculation
- **Reporting & Analytics**: Generate detailed reports on sales, inventory, and profitability
- **Backup & Restore**: Create and manage database backups with scheduled backup options
- **Import/Export**: Import and export data in Excel or CSV format
- **Responsive Design**: Modern, mobile-friendly interface

## Technology Stack

- **Backend**: Python with Flask framework
- **Database**: SQLAlchemy ORM with SQLite (configurable for other databases)
- **Frontend**: Bootstrap 5, HTML, CSS, JavaScript
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **Database Migrations**: Flask-Migrate

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/inventory-management.git
   cd inventory-management
   ```

2. Create and activate a virtual environment:
   ```
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python run.py
   ```

5. Access the application in your web browser at `http://localhost:5000`

For more detailed installation instructions, see [INSTALL.md](INSTALL.md).

## Usage

### Getting Started

1. Register a new account (the first account created will be assigned admin privileges)
2. Log in with your credentials
3. Add sales platforms you use (eBay, Craigslist, etc.)
4. Add inventory items with details like cost, condition, and quantity
5. Create listings for your items on different platforms
6. Record sales transactions as they occur
7. Generate reports to analyze your business performance

### Key Workflows

- **Adding Inventory**: Navigate to Inventory → Add Item to add new items to your inventory
- **Creating Listings**: From an item's detail page, click "Create Listing" to list it on a sales platform
- **Recording Sales**: When an item sells, navigate to the listing and click "Mark as Sold" to record the transaction
- **Generating Reports**: Use the Reports section to analyze sales performance, inventory aging, and profitability

## Screenshots

(Screenshots will be added here)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
