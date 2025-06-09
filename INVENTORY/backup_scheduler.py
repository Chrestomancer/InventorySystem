#!/usr/bin/env python
"""
Backup Scheduler Script for Inventory Management System

This script checks the backup schedule configuration and creates a backup
if needed. It should be run by a scheduler (cron job or Windows Task Scheduler)
at regular intervals (e.g., daily).

Usage:
    python backup_scheduler.py
"""

import os
import sys
import datetime
from app import create_app
from app.utils.backup import create_backup, get_db_path

def should_run_backup(schedule_type):
    """Determine if a backup should be run based on the schedule type"""
    if schedule_type == 'none':
        return False
    
    if schedule_type == 'daily':
        # Run daily backup
        return True
    
    if schedule_type == 'weekly':
        # Run weekly backup on Sundays
        return datetime.datetime.now().weekday() == 6
    
    return False

def main():
    """Main function to run the backup scheduler"""
    # Create the Flask app context
    app = create_app()
    
    with app.app_context():
        # Check if the backup directory exists
        backup_dir = os.path.join(app.root_path, '..', 'backups')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Check the schedule configuration
        schedule_file = os.path.join(backup_dir, 'schedule.txt')
        if not os.path.exists(schedule_file):
            print("No backup schedule configured.")
            return
        
        with open(schedule_file, 'r') as f:
            schedule_type = f.read().strip()
        
        # Check if a backup should be run
        if should_run_backup(schedule_type):
            try:
                # Create a backup with a timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"scheduled_backup_{timestamp}.db"
                backup_path = create_backup(backup_name)
                print(f"Scheduled backup created: {backup_path}")
            except Exception as e:
                print(f"Error creating backup: {str(e)}")
                return 1
        else:
            print(f"No backup scheduled for today (schedule: {schedule_type}).")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
