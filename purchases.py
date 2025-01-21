from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required
from app_init import db
from models import Purchase
from datetime import datetime
from sqlalchemy import func

purchases_bp = Blueprint('purchases', __name__)

# Route to add new purchase(s)
@purchases_bp.route('/add-purchase', methods=['GET', 'POST'])
@login_required
def add_purchase():
    if request.method == 'POST':
        items = request.form.getlist('items[]')  # List of item names
        vendor = request.form.getlist('vendor[]')
        categories = request.form.getlist('categories[]')
        dates = request.form.getlist('dates[]')
        prices = request.form.getlist('prices[]')
        quantities = request.form.getlist('quantities[]')
        notes = request.form.getlist('notes[]')

        for i in range(len(items)):
            new_purchase = Purchase(
                item_name=items[i],
                vendor=vendor[i],
                category=categories[i],
                date=datetime.strptime(dates[i], "%Y-%m-%d"),
                price=float(prices[i]),
                quantity=int(quantities[i]),
                notes=notes[i]
            )
            db.session.add(new_purchase)
        
        db.session.commit()
        flash('Purchase(s) added successfully!', 'success')
        return redirect(url_for('purchases.purchase_history'))
    
    return render_template('add_purchase.html' , currentDate=datetime.now().strftime('%Y-%m-%d'))

# Route to view purchase history with pagination and date filtering
@purchases_bp.route('/purchase-history', methods=['GET', 'POST'])
@login_required
def purchase_history():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    query = Purchase.query
    if start_date and end_date:
        query = query.filter(func.date(Purchase.date) >= start_date, func.date(Purchase.date) <= end_date)

    purchases = query.order_by(Purchase.date.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('purchase_history.html', purchases=purchases, start_date=start_date, end_date=end_date , currentDate=datetime.now().strftime('%Y-%m-%d'))
