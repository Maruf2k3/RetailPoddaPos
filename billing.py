import csv
import io
import uuid
from datetime import datetime

from flask import Blueprint, Response, json, render_template, redirect, send_file, url_for, flash, request
from flask_login import login_required, current_user
import pytz
from sqlalchemy import func

from models import db, Sale, Customer, Group, GroupSale, MenuItem

billing_bp = Blueprint('billing', __name__)

def merge_sale_items(items_list):
    """
    Merge repeated items by (name, price) only.
    Ignores served_by if present in the data.
    """
    merged = {}
    for item in items_list:
        name = item.get('name', '')
        price = float(item.get('price', 0.0))
        qty = int(item.get('qty', 1))

        key = (name, price)  # ignoring served_by
        if key not in merged:
            merged[key] = {
                "name": name,
                "price": price,
                "qty": 0
            }
        merged[key]["qty"] += qty

    return list(merged.values())

@billing_bp.route("/create-bill", methods=['GET', 'POST'])
@login_required
def create_bill():
    if current_user.role not in ['staff', 'manager', 'admin']:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        customer_id = request.form.get('customer')
        group_id = request.form.get('group')
        note = request.form.get('note')
        discount = float(request.form.get('discount', 0))
        tax_from_html = float(request.form.get('tax', 0))
        payment_method = request.form.get('payment-method', 'cash')

        customer = Customer.query.get(customer_id) if customer_id else None
        group = Group.query.get(group_id) if group_id else None

        items_str = request.form.get('items', '[]')
        try:
            items_list = json.loads(items_str)
        except json.JSONDecodeError:
            flash('Error parsing items.', 'error')
            return redirect(url_for('billing.create_bill'))

        # Merge repeated items by (name, price) only
        merged_items = merge_sale_items(items_list)
        if not all('price' in item and 'qty' in item for item in merged_items):
            flash('Error: Items data is incomplete.', 'error')
            return redirect(url_for('billing.create_bill'))

        subtotal = sum(item['price'] * item['qty'] for item in merged_items)
        tax = (tax_from_html / 100) * subtotal
        grand_total = subtotal + tax - discount

        invoice_number = str(uuid.uuid4())
        server = current_user.username
        current_time_uae = datetime.now(pytz.timezone("Asia/Dubai"))
        merged_items_json = json.dumps(merged_items)

        # Bill for a Customer
        if customer:
            new_sale = Sale(
                invoice_number=invoice_number,
                date=current_time_uae.strftime("%Y-%m-%d"),
                time=current_time_uae.strftime("%H:%M:%S"),
                items=merged_items_json,
                subtotal=subtotal,
                tax=tax,
                grand_total=grand_total,
                discount=discount,
                notes=note,
                server=server,
                customer_id=customer.id,
                payment_method=payment_method
            )
            db.session.add(new_sale)
        # Bill for a Group
        elif group:
            new_group_sale = GroupSale(
                invoice_number=invoice_number,
                date=current_time_uae.strftime("%Y-%m-%d"),
                time=current_time_uae.strftime("%H:%M:%S"),
                items=merged_items_json,
                subtotal=subtotal,
                tax=tax,
                grand_total=grand_total,
                discount=discount,
                group_id=group.id,
                payment_method=payment_method,
                server=server,
                notes=note
            )
            group.total_due += grand_total
            db.session.add(new_group_sale)
        # Walk-in / No customer or group
        else:
            new_sale = Sale(
                invoice_number=invoice_number,
                date=current_time_uae.strftime("%Y-%m-%d"),
                time=current_time_uae.strftime("%H:%M:%S"),
                items=merged_items_json,
                subtotal=subtotal,
                tax=tax,
                grand_total=grand_total,
                discount=discount,
                notes=note,
                server=server,
                customer_id=None,
                payment_method=payment_method
            )
            db.session.add(new_sale)

        db.session.commit()
        flash('Bill created successfully!', 'success')
        return redirect(url_for('auth.dashboard'))

    # For GET request
    customers = Customer.query.all()
    groups = Group.query.all()
    menu_items = MenuItem.query.all()
    return render_template('create_bill.html', customers=customers, groups=groups, menu_items=menu_items)


# ------------------------------------- Sales Reports ---------------------------- #

# 2. JSON Filter for Items in Templates
def fromjson_filter(s):
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return {}


# 3. Sales Report with Date Filtering
@billing_bp.route("/sales-reports", methods=['GET', 'POST'])
@login_required
def sales_reports():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 15
    sales = None
    start_date_str = request.form.get('start_date') if request.method == 'POST' else request.args.get('start_date')
    end_date_str = request.form.get('end_date') if request.method == 'POST' else request.args.get('end_date')

    if start_date_str and end_date_str:
        try:
            datetime.strptime(start_date_str, '%Y-%m-%d')
            datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('billing.sales_reports'))

        sales = Sale.query.filter(
            func.date(Sale.date) >= start_date_str,
            func.date(Sale.date) <= end_date_str
        ).order_by(Sale.date.desc()).paginate(page=page, per_page=per_page)

        if not sales.items and page == 1:
            flash('No sales found within the selected date range.', 'error')

    return render_template('sales_reports.html', sales=sales, start_date=start_date_str, end_date=end_date_str)


# 4. Predefined Sales Reports
@billing_bp.route("/sales-reports/predefined/<string:range_type>", methods=['GET'])
@login_required
def sales_reports_predefined(range_type):
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 15
    today = datetime.now().date()

    if range_type == 'today':
        start_date = end_date = today
    elif range_type == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif range_type == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:
        flash('Invalid range type.', 'error')
        return redirect(url_for('billing.sales_reports'))

    sales = Sale.query.filter(
        func.date(Sale.date) >= start_date,
        func.date(Sale.date) <= end_date
    ).order_by(Sale.date.desc()).paginate(page=page, per_page=per_page)

    if not sales.items and page == 1:
        flash('No sales found for the selected range.', 'error')

    return render_template('sales_reports.html', sales=sales, range_type=range_type, start_date=start_date, end_date=end_date)


# 5. Download Sales Report as CSV
@billing_bp.route("/download-sales-report", methods=['GET'])
@login_required
def download_sales_report():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        flash('Invalid date range for report download.', 'error')
        return redirect(url_for('billing.sales_reports'))

    try:
        datetime.strptime(start_date_str, '%Y-%m-%d')
        datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('billing.sales_reports'))

    sales = Sale.query.filter(
        func.date(Sale.date) >= start_date_str,
        func.date(Sale.date) <= end_date_str
    ).all()

    if not sales:
        flash('No sales found within the selected date range.', 'error')
        return redirect(url_for('billing.sales_reports'))

    output = io.StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(['Invoice Number', 'Date', 'Time', 'Customer', 'Items', 'Subtotal', 'Tax', 'Discount', 'Grand Total', 'Served By', 'Payment Method', 'Notes'])

    for sale in sales:
        customer_name = sale.customer.name if sale.customer else "Walk In"
        items = json.loads(sale.items)
        item_list = "; ".join([f"{item['name']} (Qty: {item.get('qty', 1)})" for item in items])

        csv_writer.writerow([
            sale.invoice_number,
            sale.date,
            sale.time,
            customer_name,
            item_list,
            sale.subtotal,
            sale.tax,
            sale.discount,
            sale.grand_total,
            sale.server,
            sale.payment_method,
            sale.notes
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=salesReport_{start_date_str}_{end_date_str}.csv'}
    )


# 8.4 Route to delete a customer sale
@billing_bp.route('/delete-sale/<int:sale_id>', methods=['POST'])
@login_required
def delete_sale(sale_id):
    if current_user.role not in ['admin']:
        return redirect(url_for('auth.dashboard'))

    sale = Sale.query.get_or_404(sale_id)
    db.session.delete(sale)
    db.session.commit()
    flash('Sale deleted successfully!', 'success')
    return redirect(url_for('billing.sales_reports'))


@billing_bp.route('/get-sale/<int:sale_id>', methods=['GET'])
@login_required
def get_sale(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    sale_data = {
        "id": sale.id,
        "date": sale.date,
        "time": sale.time,
        "customer": sale.customer.name if sale.customer else "Walk In",
        "server": sale.server,
        "subtotal": sale.subtotal,
        "tax": sale.tax,
        "discount": sale.discount,
        "grand_total": sale.grand_total,
        "items": json.loads(sale.items),
        "invoice_number": sale.invoice_number
    }
    return sale_data


@billing_bp.route("/all-sales-reports", methods=['GET', 'POST'])
@login_required
def all_sales_reports():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 15
    range_type = request.form.get('range_type', 'all')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    # Handle predefined date ranges
    today = datetime.now().date()
    if range_type == 'today':
        start_date, end_date = today, today
    elif range_type == 'month':
        start_date, end_date = today.replace(day=1), today
    elif range_type == 'year':
        start_date, end_date = today.replace(month=1, day=1), today
    elif start_date and end_date:
        # Custom date range provided, parse and use
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('billing.all_sales_reports'))
    else:
        # If no valid date is provided, default to all records
        start_date, end_date = None, None

    # Query for sales and group sales based on date filter
    sales_query = Sale.query
    group_sales_query = GroupSale.query
    if start_date and end_date:
        sales_query = sales_query.filter(Sale.date.between(start_date, end_date))
        group_sales_query = group_sales_query.filter(GroupSale.date.between(start_date, end_date))

    # Pagination for both results
    sales = sales_query.order_by(Sale.date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    group_sales = group_sales_query.order_by(GroupSale.date.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'All_sales.html',
        sales=sales,
        group_sales=group_sales,
        start_date=start_date,
        end_date=end_date,
        range_type=range_type
    )


@billing_bp.route("/download-all-sales", methods=['GET'])
@login_required
def download_all_sales():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    range_type = request.args.get('range_type', 'all')

    # Ensure start_date and end_date are parsed
    sales_query = Sale.query
    group_sales_query = GroupSale.query

    if start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            sales_query = sales_query.filter(Sale.date.between(start_date_obj, end_date_obj))
            group_sales_query = group_sales_query.filter(GroupSale.date.between(start_date_obj, end_date_obj))
        except ValueError:
            flash('Invalid date format for download.', 'error')
            return redirect(url_for('billing.all_sales_reports'))

    sales = sales_query.all()
    group_sales = group_sales_query.all()

    # CSV output
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Invoice Number', 'Date', 'Time', 'Items', 'Subtotal', 'Tax', 'Grand Total', 'Discount', 'Payment Method', 'Notes'])

    for sale in sales:
        items = json.loads(sale.items)
        item_str = ', '.join([f"{item['name']} (Qty: {item['qty']})" for item in items])
        writer.writerow([
            sale.invoice_number,
            sale.date,
            sale.time,
            item_str,
            sale.subtotal,
            sale.tax,
            sale.grand_total,
            sale.discount,
            sale.payment_method,
            sale.notes
        ])

    for group_sale in group_sales:
        items = json.loads(group_sale.items)
        item_str = ', '.join([f"{item['name']} (Qty: {item['qty']})" for item in items])
        writer.writerow([
            group_sale.invoice_number,
            group_sale.date,
            group_sale.time,
            item_str,
            group_sale.subtotal,
            group_sale.tax,
            group_sale.grand_total,
            group_sale.discount,
            group_sale.payment_method,
            group_sale.notes
        ])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='all_sales_report.csv')
