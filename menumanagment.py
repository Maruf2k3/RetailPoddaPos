from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import openpyxl
from models import db, MenuItem

menu_bp = Blueprint('menu_management', __name__)

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Menu Management Route
@menu_bp.route("/menu-management", methods=['GET', 'POST'])
@login_required
def menu_management():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        # Handle Excel upload
        if 'file' in request.files:
            file = request.files.get('file')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join('static', 'uploads', filename)
                file.save(filepath)

                try:
                    workbook = openpyxl.load_workbook(filepath)
                    sheet = workbook.active
                    for row in sheet.iter_rows(min_row=2, values_only=True):
                        name, price, category = row
                        # Check if the item already exists
                        existing_item = MenuItem.query.filter_by(name=name).first()
                        if existing_item:
                            flash(f"Item '{name}' already exists in the database.", 'warning')
                        else:
                            new_item = MenuItem(name=name, price=float(price), category=category)
                            db.session.add(new_item)
                    db.session.commit()
                    flash('Menu uploaded successfully!', 'success')
                except Exception as e:
                    flash(f"Error processing the file: {str(e)}", 'error')
                finally:
                    os.remove(filepath)

        # Handle single item addition
        else:
            name = request.form.get('name')
            price = request.form.get('price')
            category = request.form.get('category')

            if name and price and category:
                existing_item = MenuItem.query.filter_by(name=name).first()
                if existing_item:
                    flash(f"Item '{name}' already exists in the menu.", 'error')
                else:
                    new_item = MenuItem(name=name, price=float(price), category=category)
                    db.session.add(new_item)
                    db.session.commit()
                    flash('Item added successfully!', 'success')

    menu_items = MenuItem.query.all()
    return render_template('menumanagment.html', menu_items=menu_items)

# Edit Menu Item Route
@menu_bp.route("/menu-management/edit/<int:item_id>", methods=['POST'])
@login_required
def edit_menu_item(item_id):
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('dashboard'))

    menu_item = MenuItem.query.get_or_404(item_id)
    
    name = request.form.get('name')
    price = request.form.get('price')
    category = request.form.get('category')

    if name and price and category:
        existing_item = MenuItem.query.filter_by(name=name).first()
        if existing_item and existing_item.id != item_id:
            flash(f"Item '{name}' already exists in the database.", 'warning')
        else:
            menu_item.name = name
            menu_item.price = float(price)
            menu_item.category = category
            db.session.commit()
            flash('Menu item updated successfully!', 'success')
    else:
        flash('All fields are required!', 'error')

    return redirect(url_for('menu_management.menu_management'))

# Delete Menu Item Route
@menu_bp.route("/menu-management/delete/<int:item_id>", methods=['POST'])
@login_required
def delete_menu_item(item_id):
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('dashboard'))

    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('menu_management.menu_management'))
