from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from urllib.parse import urlparse
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False) == 'on'

        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))

        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()

        login_user(user, remember=remember)

        # Redirect to the page the user was trying to access
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('main.dashboard')

        return redirect(next_page)

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Check if username or email already exists
        user_exists = User.query.filter_by(username=username).first()
        email_exists = User.query.filter_by(email=email).first()

        if user_exists:
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))

        if email_exists:
            flash('Email already exists', 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.register'))

        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return redirect(url_for('auth.register'))

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)

        # First user is admin
        if User.query.count() == 0:
            user.role = 'admin'

        db.session.add(user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile route"""
    return render_template('auth/profile.html')

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile route"""
    if request.method == 'POST':
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Check if email already exists (for another user)
        email_exists = User.query.filter(User.email == email, User.id != current_user.id).first()

        if email_exists:
            flash('Email already exists', 'danger')
            return redirect(url_for('auth.edit_profile'))

        # Update email
        if email != current_user.email:
            current_user.email = email

        # Update password if provided
        if current_password and new_password and confirm_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect', 'danger')
                return redirect(url_for('auth.edit_profile'))

            if new_password != confirm_password:
                flash('New passwords do not match', 'danger')
                return redirect(url_for('auth.edit_profile'))

            if len(new_password) < 8:
                flash('New password must be at least 8 characters long', 'danger')
                return redirect(url_for('auth.edit_profile'))

            current_user.set_password(new_password)

        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/edit_profile.html')
