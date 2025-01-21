from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from flask_login import login_required, current_user
import pytz
from menumanagment import allowed_file
from models import db, Inventory, InventoryLog
from werkzeug.utils import secure_filename
import os, io, csv
from datetime import datetime
import openpyxl
from collections import OrderedDict

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/inventory-dashboard', methods=['GET', 'POST'])
@login_required
def inventory_dashboard():
    if request.method == 'POST':
        if current_user.role != 'admin':
            flash('Only admin can add inventory items.', 'error')
            return redirect(url_for('inventory.inventory_dashboard'))

        name = request.form.get('name').strip()
        quantity = request.form.get('quantity')
        unit = request.form.get('unit')

        try:
            quantity = float(quantity)
            if quantity <= 0:
                flash('Quantity must be greater than zero.', 'error')
                return redirect(url_for('inventory.inventory_dashboard'))
        except ValueError:
            flash('Invalid quantity.', 'error')
            return redirect(url_for('inventory.inventory_dashboard'))

        existing_item = Inventory.query.filter_by(name=name).first()
        if existing_item:
            flash(f"Item '{name}' already exists. Consider editing instead.", 'error')
        else:
            new_item = Inventory(name=name, quantity=quantity, unit=unit)
            db.session.add(new_item)
            db.session.commit()
            flash(f"Added '{name}' to inventory.", 'success')

    inventory_items = Inventory.query.all()
    return render_template('inventory_dashboard.html', inventory_items=inventory_items)


@inventory_bp.route('/upload-inventory', methods=['POST'])
@login_required
def upload_inventory():
    if current_user.role != 'admin':
        flash('Only admin can upload inventory via Excel.', 'error')
        return redirect(url_for('inventory.inventory_dashboard'))

    file = request.files.get('file')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join('static', 'uploads', filename)
        file.save(filepath)

        try:
            workbook = openpyxl.load_workbook(filepath)
            sheet = workbook.active
            for row in sheet.iter_rows(min_row=2, values_only=True):
                name, quantity, unit = row
                existing_item = Inventory.query.filter_by(name=name).first()
                if existing_item:
                    existing_item.add_quantity(float(quantity))
                else:
                    new_item = Inventory(name=name, quantity=float(quantity), unit=unit)
                    db.session.add(new_item)
            db.session.commit()
            flash('Inventory updated from Excel.', 'success')
        except Exception as e:
            flash(f"Error processing file: {str(e)}", 'error')
        finally:
            os.remove(filepath)

    return redirect(url_for('inventory.inventory_dashboard'))


@inventory_bp.route('/log-inventory-usage', methods=['GET', 'POST'])
@login_required
def log_usage():
    inventory_items = Inventory.query.all()
    if request.method == 'POST':
        item_ids = request.form.getlist('item_id[]')
        used_quantities = request.form.getlist('used_quantity[]')
        usage_dates = request.form.getlist('usage_date[]')
        notes_list = request.form.getlist('notes[]')

        for i in range(len(item_ids)):
            item_id = item_ids[i]
            used_quantity = float(used_quantities[i])
            usage_date = datetime.strptime(usage_dates[i], '%Y-%m-%d')
            notes = notes_list[i] if i < len(notes_list) else ""

            item = Inventory.query.get(item_id)
            if item and item.quantity >= used_quantity:
                item.subtract_quantity(used_quantity)
                log = InventoryLog(item_id=item.id, used_quantity=used_quantity, date=usage_date, notes=notes)
                db.session.add(log)
                db.session.commit()
                flash(f"Used {used_quantity} {item.unit} of {item.name}.", 'success')
            else:
                flash(f"Not enough quantity for {item.name}.", 'error')

        return redirect(url_for('inventory.view_usage_logs'))

    return render_template('log_usage.html', inventory_items=inventory_items, current_date=datetime.now().strftime('%Y-%m-%d'))



@inventory_bp.route('/inventory-usage-logs', defaults={'page': 1})
@inventory_bp.route('/inventory-usage-logs/page/<int:page>')
@login_required
def view_usage_logs(page):
    # Check if a specific date is requested
    date_str = request.args.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            logs = InventoryLog.query.filter(db.func.date(InventoryLog.date) == selected_date).all()
            
            if not logs:
                flash("No logs available for the selected date.", "info")
                return redirect(url_for('inventory.view_usage_logs', page=1))

            return render_template(
                'inventory_usage.html',
                current_date_logs=(date_str, logs),
                page=page,
                total_pages=1,  # only one page for the selected date
                current_date=datetime.now().strftime('%Y-%m-%d')  # Pass current date for max attribute
            )
        except ValueError:
            flash("Invalid date format.", "error")
            return redirect(url_for('inventory.view_usage_logs', page=1))

    # Fallback to normal pagination if no specific date is chosen
    logs = InventoryLog.query.order_by(InventoryLog.date.desc()).all()
    
    # Group logs by date
    grouped_logs = OrderedDict()
    for log in logs:
        date_str = log.date.strftime('%Y-%m-%d')
        if date_str not in grouped_logs:
            grouped_logs[date_str] = []
        grouped_logs[date_str].append(log)

    grouped_logs_list = list(grouped_logs.items())
    total_dates = len(grouped_logs_list)

    # Check if requested page is out of range
    if page < 1 or page > total_dates:
        return redirect(url_for('inventory.view_usage_logs', page=1))

    current_date_logs = grouped_logs_list[page - 1]
    
    return render_template(
        'inventory_usage.html',
        current_date_logs=current_date_logs,
        page=page,
        total_pages=total_dates,
        current_date=datetime.now().strftime('%Y-%m-%d')  # Pass current date for max attribute
    )




@inventory_bp.route('/delete-inventory/<int:item_id>', methods=['POST'])
@login_required
def delete_inventory(item_id):
    if current_user.role != 'admin':
        flash('Only admin can delete inventory item.', 'error')
        return redirect(url_for('inventory.inventory_dashboard'))

    item = Inventory.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash(f"Deleted '{item.name}' from inventory.", 'success')
    else:
        flash("Item not found.", 'error')
    return redirect(url_for('inventory.inventory_dashboard'))


@inventory_bp.route('/edit-inventory', methods=['POST'])
@login_required
def edit_inventory():
    if current_user.role != 'admin':
        flash('Only admin can Edit inventory item.', 'error')
        return redirect(url_for('inventory.inventory_dashboard'))

    item_id = request.form.get('item_id')
    name = request.form.get('name').strip()
    quantity = float(request.form.get('quantity'))
    unit = request.form.get('unit')

    item = Inventory.query.get(item_id)
    if item:
        item.name = name
        item.quantity = quantity
        item.unit = unit
        item.last_modified = datetime.now(pytz.timezone("Asia/Dubai"))
        db.session.commit()
        flash(f"Updated '{item.name}' in inventory.", 'success')
    else:
        flash("Item not found.", 'error')

    return redirect(url_for('inventory.inventory_dashboard'))


@inventory_bp.route('/download-inventory', methods=['GET'])
@login_required
def download_inventory():
    if current_user.role != 'admin':
        flash(f'Your role: {current_user.role}. No download access.', 'error')
        return redirect(url_for('inventory.inventory_dashboard'))

    inventory_items = Inventory.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Item Name', 'Quantity', 'Unit'])
    for item in inventory_items:
        writer.writerow([item.name, item.quantity, item.unit])
    output.seek(0)

    return Response(output, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=inventory.csv'})
