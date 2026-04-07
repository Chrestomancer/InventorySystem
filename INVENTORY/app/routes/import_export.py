from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.utils.file_io import (
    export_data, import_inventory, import_platforms, create_sample_template
)
import os

import_export_bp = Blueprint('import_export', __name__)

@import_export_bp.route('/')
@login_required
def index():
    """Import/Export main page"""
    return render_template('import_export/index.html')

@import_export_bp.route('/export', methods=['POST'])
@login_required
def export():
    """Export data to Excel or CSV"""
    data_type = request.form.get('data_type', 'all')
    file_format = request.form.get('file_format', 'excel')

    try:
        return export_data(data_type, file_format)
    except Exception as e:
        flash(f'Error exporting data: {str(e)}', 'danger')
        return redirect(url_for('import_export.index'))

@import_export_bp.route('/import', methods=['POST'])
@login_required
def import_data():
    """Import data from Excel or CSV"""
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('import_export.index'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('import_export.index'))

    # Validate file extension
    allowed_extensions = {'.xlsx', '.xls', '.csv'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        flash('Unsupported file type. Please upload an Excel (.xlsx, .xls) or CSV (.csv) file.', 'danger')
        return redirect(url_for('import_export.index'))

    data_type = request.form.get('data_type', 'inventory')

    try:
        if data_type == 'inventory':
            success, result = import_inventory(file)
        elif data_type == 'platforms':
            success, result = import_platforms(file)
        else:
            flash(f'Unknown import type: {data_type}', 'danger')
            return redirect(url_for('import_export.index'))

        if success:
            if isinstance(result, dict):
                flash(f'Import completed: {result["success"]} items added, {result["updated"]} items updated, {len(result["errors"])} errors', 'success')
                if result["errors"]:
                    for error in result["errors"]:
                        flash(error, 'warning')
            else:
                flash(f'Import completed successfully', 'success')
        else:
            flash(f'Import failed: {result}', 'danger')

        return redirect(url_for('import_export.index'))

    except Exception as e:
        flash(f'Error importing data: {str(e)}', 'danger')
        return redirect(url_for('import_export.index'))

@import_export_bp.route('/template/<data_type>')
@login_required
def get_template(data_type):
    """Get a sample template for import"""
    file_format = request.args.get('format', 'excel')

    try:
        return create_sample_template(data_type, file_format)
    except Exception as e:
        flash(f'Error creating template: {str(e)}', 'danger')
        return redirect(url_for('import_export.index'))
