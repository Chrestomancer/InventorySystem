from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import login_required, current_user
from app.utils.backup import create_backup, list_backups, restore_backup
import os

backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/')
@login_required
def index():
    """Backup management page"""
    if not current_user.is_admin():
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.dashboard'))

    backups = list_backups()
    return render_template('backup/index.html', backups=backups)

@backup_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Create a new backup"""
    if not current_user.is_admin():
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.dashboard'))

    custom_name = request.form.get('backup_name')
    if custom_name and not custom_name.endswith('.db'):
        custom_name += '.db'

    try:
        backup_path = create_backup(custom_name)
        flash(f'Backup created successfully: {os.path.basename(backup_path)}', 'success')
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'danger')

    return redirect(url_for('backup.index'))

@backup_bp.route('/restore/<filename>', methods=['POST'])
@login_required
def restore(filename):
    """Restore from a backup"""
    if not current_user.is_admin():
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.dashboard'))

    success, message = restore_backup(filename)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('backup.index'))

@backup_bp.route('/download/<filename>')
@login_required
def download(filename):
    """Download a backup file"""
    if not current_user.is_admin():
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.dashboard'))

    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    return send_from_directory(backup_dir, filename, as_attachment=True)

@backup_bp.route('/delete/<filename>', methods=['POST'])
@login_required
def delete(filename):
    """Delete a backup file"""
    if not current_user.is_admin():
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.dashboard'))

    backup_dir = os.path.join(current_app.root_path, '..', 'backups')
    backup_path = os.path.join(backup_dir, filename)

    if os.path.exists(backup_path):
        os.remove(backup_path)
        flash(f'Backup {filename} deleted successfully', 'success')
    else:
        flash(f'Backup file {filename} not found', 'danger')

    return redirect(url_for('backup.index'))

@backup_bp.route('/schedule', methods=['POST'])
@login_required
def schedule():
    """Schedule automatic backups"""
    if not current_user.is_admin():
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.dashboard'))

    schedule_type = request.form.get('schedule_type')

    # Store the schedule setting in a file
    schedule_file = os.path.join(current_app.root_path, '..', 'backups', 'schedule.txt')
    with open(schedule_file, 'w') as f:
        f.write(schedule_type)

    flash(f'Backup schedule set to: {schedule_type}', 'success')
    return redirect(url_for('backup.index'))
