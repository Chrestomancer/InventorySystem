import os
import shutil
import datetime
import sqlite3
from flask import current_app

def get_db_path():
    """Get the path to the database file"""
    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    db_path = None
    
    if db_uri.startswith('sqlite:///'):
        # For relative paths in SQLite URI (sqlite:///inventory.db)
        db_filename = db_uri.replace('sqlite:///', '')
        if not os.path.isabs(db_filename):
            # Check if the file exists in the instance folder first
            instance_path = os.path.join(current_app.root_path, '..', 'instance', db_filename)
            if os.path.exists(instance_path):
                db_path = instance_path
            else:
                # Fall back to the original path resolution
                db_path = os.path.join(current_app.root_path, '..', db_filename)
    else:
        # For other database types or absolute paths
        db_path = db_uri.replace('sqlite:///', '')
    
    # Ensure db_path is set
    if db_path is None:
        raise ValueError(f"Could not determine database path from URI: {db_uri}")
    
    return db_path

def create_backup(custom_name=None):
    """Create a backup of the database"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = custom_name or f"backup_{timestamp}.db"
    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    
    # Create backup directory if it doesn't exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Get the database path
    try:
        db_path = get_db_path()
    except ValueError as e:
        raise ValueError(f"Error creating backup: {str(e)}")
    
    # Destination backup path
    backup_path = os.path.join(backup_dir, backup_name)
    
    # Copy the database file
    shutil.copy2(db_path, backup_path)
    
    return backup_path

def list_backups():
    """List all available backups"""
    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    if not os.path.exists(backup_dir):
        return []
    
    backups = []
    for filename in os.listdir(backup_dir):
        if filename.endswith('.db'):
            file_path = os.path.join(backup_dir, filename)
            created_time = datetime.datetime.fromtimestamp(os.path.getctime(file_path))
            size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
            
            # Verify this is a valid SQLite database
            try:
                conn = sqlite3.connect(file_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                conn.close()
                is_valid = len(tables) > 0
            except:
                is_valid = False
            
            backups.append({
                'filename': filename,
                'path': file_path,
                'created': created_time,
                'size_mb': round(size, 2),
                'is_valid': is_valid
            })
    
    # Sort by creation time (newest first)
    backups.sort(key=lambda x: x['created'], reverse=True)
    return backups

def restore_backup(backup_filename):
    """Restore the database from a backup file"""
    # Sanitize filename to prevent path traversal
    backup_filename = os.path.basename(backup_filename)
    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    backup_dir = os.path.realpath(backup_dir)
    backup_path = os.path.join(backup_dir, backup_filename)
    
    if not os.path.exists(backup_path):
        return False, f"Backup file {backup_filename} not found"
    
    # Verify this is a valid SQLite database
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        if len(tables) == 0:
            return False, "Invalid backup file: No tables found"
    except Exception as e:
        return False, f"Invalid backup file: {str(e)}"
    
    # Get the database path
    try:
        db_path = get_db_path()
    except ValueError as e:
        return False, f"Error restoring backup: {str(e)}"
    
    # Create a backup of the current database before restoring
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    current_backup = os.path.join(backup_dir, f"pre_restore_{timestamp}.db")
    shutil.copy2(db_path, current_backup)
    
    # Restore the database
    shutil.copy2(backup_path, db_path)
    
    return True, "Database restored successfully"
