from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from flask_jwt_extended import create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies, unset_jwt_cookies
from models import User, db
from forms import LoginForm, RegisterForm
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

auth_bp = Blueprint('auth', __name__)

# Register Route
@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        existing_admin = User.query.filter_by(role='admin').first()
        if user:
            flash('Username already exists.', 'error')
            return render_template('register.html', form=form)
        if form.role.data == 'admin' and existing_admin:
            flash('Only one admin is allowed.', 'error')
            return render_template('register.html', form=form)
        
        new_user = User(username=form.username.data, role=form.role.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Registered successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)

# Login Route
@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            response = redirect(url_for('auth.dashboard'))
            set_access_cookies(response, access_token)
            set_refresh_cookies(response, refresh_token)
            flash('Logged in successfully', 'success')
            return response
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html', form=form)

# Dashboard Route
@auth_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == "admin":
        return render_template('adminDash.html', role="admin" , name = f'{current_user.username}')

    elif current_user.role == "manager":
        return render_template('managerDash.html', role="manager" , name = f'{current_user.username}')

    elif current_user.role == "staff":
        return render_template('staffDash.html', role="staff" , name = f'{current_user.username}')

    else:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('auth.login'))

# Logout Route
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    response = redirect(url_for('auth.login'))
    unset_jwt_cookies(response)
    flash('Logged out successfully.', 'success')
    return response




