from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Customer, Sale

crm_bp = Blueprint('crm', __name__)

@crm_bp.route("/customer-management", methods=['GET', 'POST'])
@login_required
def customer_management():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')
        # Add, Edit, or Delete customer based on action
        if action == 'add':
            new_customer = Customer(name=request.form['name'], phone_number=request.form['phone_number'])
            db.session.add(new_customer)
            db.session.commit()
            flash('Customer added successfully!', 'success')
        elif action == 'edit':
            customer = Customer.query.get(request.form['customer_id'])
            customer.name = request.form['name']
            customer.phone_number = request.form['phone_number']
            db.session.commit()
            flash('Customer updated successfully!', 'success')
        elif action == 'delete':
            customer = Customer.query.get(request.form['customer_id'])
            db.session.delete(customer)
            db.session.commit()
            flash('Customer deleted successfully!', 'success')

    customers = Customer.query.all()
    return render_template('customer_management.html', customers=customers)

@crm_bp.route("/customer-history", methods=['GET', 'POST'])
@login_required
def customer_history():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    customers = Customer.query.all()
    sales_history = None
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        history_type = request.form.get('history_type')
        customer = Customer.query.get(customer_id)
        if history_type == 'date_range':
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            sales_history = Sale.query.filter(Sale.customer_id == customer_id, Sale.date.between(start_date, end_date)).all()
        else:
            sales_history = Sale.query.filter_by(customer_id=customer_id).all()

    return render_template('customer_history.html', customers=customers, sales_history=sales_history)
