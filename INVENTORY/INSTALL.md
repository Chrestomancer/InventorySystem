# Installation Guide for Inventory Management System

This guide will help you set up and run the Inventory Management System on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.8 or higher
- pip (Python package installer)
- Git (optional, for cloning the repository)

## Installation Steps

### 1. Clone or Download the Repository

```bash
git clone https://github.com/yourusername/inventory-management.git
cd inventory-management
```

Or download and extract the ZIP file from the repository.

### 2. Create a Virtual Environment

It's recommended to use a virtual environment to keep dependencies required by this project separate from other projects.

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install all required packages using pip:

```bash
pip install -r requirements.txt
```

### 4. Initialize the Database

The application uses SQLite by default, which doesn't require any additional setup. The database will be created automatically when you first run the application.

### 5. Run the Application

Start the Flask development server:

```bash
python run.py
```

The application should now be running at `http://localhost:5000`.

### 6. First-Time Setup

1. Open your web browser and navigate to `http://localhost:5000`
2. Register a new account (the first account created will automatically be assigned admin privileges)
3. Log in with your new account
4. Start adding inventory items, sales platforms, and listings

## Configuration Options

### Environment Variables

You can customize the application by setting the following environment variables:

- `SECRET_KEY`: Used for securely signing session cookies (default: 'dev-key-for-testing')
- `DATABASE_URI`: Database connection URI (default: SQLite database in the application directory)
- `DEBUG`: Set to 'True' for development mode, 'False' for production (default: 'True')

Example (on Windows):
```
set SECRET_KEY=your-secret-key
set DATABASE_URI=sqlite:///path/to/your/database.db
set DEBUG=False
```

Example (on macOS/Linux):
```
export SECRET_KEY=your-secret-key
export DATABASE_URI=sqlite:///path/to/your/database.db
export DEBUG=False
```

### Using a Different Database

By default, the application uses SQLite. If you want to use a different database like PostgreSQL or MySQL, you'll need to:

1. Install the appropriate database driver:
   ```
   # For PostgreSQL
   pip install psycopg2-binary
   
   # For MySQL
   pip install mysqlclient
   ```

2. Set the `DATABASE_URI` environment variable to point to your database:
   ```
   # PostgreSQL example
   export DATABASE_URI=postgresql://username:password@localhost/dbname
   
   # MySQL example
   export DATABASE_URI=mysql://username:password@localhost/dbname
   ```

## Setting Up Scheduled Backups

The application includes a backup system that can automatically create database backups on a schedule. To set this up:

### 1. Configure Backup Schedule in the Application

1. Log in as an admin user
2. Navigate to the "Backup & Restore" page from the user dropdown menu
3. Select your preferred backup schedule (Daily or Weekly)
4. Click "Save Schedule"

### 2. Set Up the Scheduler

#### On Windows (Task Scheduler)

1. Open Task Scheduler
2. Click "Create Basic Task"
3. Name it "Inventory System Backup" and click Next
4. Select "Daily" and click Next
5. Choose a start time (e.g., 3:00 AM) and click Next
6. Select "Start a Program" and click Next
7. Browse to your Python executable in your virtual environment (e.g., `C:\path\to\venv\Scripts\python.exe`)
8. In "Add arguments", enter the path to the backup scheduler script (e.g., `C:\path\to\inventory-management\backup_scheduler.py`)
9. In "Start in", enter the directory of your application (e.g., `C:\path\to\inventory-management`)
10. Click Next, then Finish

#### On macOS/Linux (Cron)

1. Open your terminal
2. Edit your crontab file:
   ```
   crontab -e
   ```
3. Add a line to run the backup script daily (e.g., at 3:00 AM):
   ```
   0 3 * * * cd /path/to/inventory-management && /path/to/venv/bin/python backup_scheduler.py >> /path/to/inventory-management/backups/backup.log 2>&1
   ```
4. Save and exit

### 3. Verify Backup Creation

After setting up the scheduler, you can verify that backups are being created by:

1. Checking the "Available Backups" section on the "Backup & Restore" page
2. Looking in the `backups` directory in your application folder

## Import/Export Functionality

The application includes functionality to import and export data in Excel and CSV formats. This allows you to:

1. Export your inventory, platforms, listings, and sales data for backup or analysis
2. Import inventory items and sales platforms from Excel or CSV files
3. Download sample templates to see the required format for importing data

### Using the Import/Export Feature

1. Navigate to the "Import/Export" page from the main navigation menu
2. For exporting:
   - Select the data you want to export
   - Choose the export format (Excel or CSV)
   - Click "Export" to download the file
3. For importing:
   - Select the type of data you want to import (inventory or platforms)
   - Upload your Excel or CSV file
   - Click "Import" to process the file

### Import File Format

When importing data, your file should include the following columns:

#### For Inventory Items:
- `Name` (required for new items)
- `SKU` (used to identify existing items)
- `Description` (optional)
- `Condition` (optional)
- `Cost Price` (optional)
- `Quantity` (optional)
- `Location` (optional)

#### For Sales Platforms:
- `Name` (required)
- `URL` (optional)
- `Fee Percentage` (optional)

You can download sample templates from the Import/Export page to see the exact format required.

## Troubleshooting

### Common Issues

1. **Package installation errors**: Make sure you're using the latest version of pip:
   ```
   pip install --upgrade pip
   ```

2. **Database errors**: If you encounter database errors, try deleting the existing database file and let the application create a new one:
   ```
   # Remove the SQLite database file
   rm instance/inventory.db
   ```

3. **Port already in use**: If port 5000 is already in use, you can specify a different port:
   ```
   # On Windows
   set FLASK_RUN_PORT=5001
   
   # On macOS/Linux
   export FLASK_RUN_PORT=5001
   ```

### Getting Help

If you encounter any issues not covered in this guide, please:

1. Check the project's README.md file for additional information
2. Look for similar issues in the project's issue tracker
3. Create a new issue with a detailed description of your problem

## Deployment to Production

For production deployment, consider the following:

1. Use a production WSGI server like Gunicorn or uWSGI instead of Flask's built-in server
2. Set up a reverse proxy with Nginx or Apache
3. Use a production-ready database like PostgreSQL
4. Set `DEBUG=False` in your environment variables
5. Generate a strong, random `SECRET_KEY`
6. Consider using environment variables for sensitive configuration

Example production setup with Gunicorn and Nginx:

1. Install Gunicorn:
   ```
   pip install gunicorn
   ```

2. Run with Gunicorn:
   ```
   gunicorn -w 4 'app:create_app()'
   ```

3. Configure Nginx as a reverse proxy to Gunicorn.

For more detailed deployment instructions, refer to the Flask documentation: https://flask.palletsprojects.com/en/2.0.x/deploying/
