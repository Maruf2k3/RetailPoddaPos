from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from models import db, Group, GroupSale, GroupPayment
from datetime import datetime
import io, csv, json
from sqlalchemy import func
import pytz

# Blueprint for groups
groups_bp = Blueprint('groups', __name__)

# 1. Route for Group Sales Reports
@groups_bp.route("/group-sales-reports", methods=['GET', 'POST'])
@login_required
def group_sales_reports():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    group_sales = []
    start_date_str = None
    end_date_str = None
    group_id = None

    if request.method == 'POST':
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        group_id = request.form.get('group_id')

        try:
            datetime.strptime(start_date_str, '%Y-%m-%d')
            datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('groups.group_sales_reports'))

        query = GroupSale.query.filter(
            func.date(GroupSale.date) >= start_date_str.strip(),
            func.date(GroupSale.date) <= end_date_str.strip()
        )
        if group_id:
            query = query.filter(GroupSale.group_id == group_id)

        group_sales = query.all()

        if not group_sales:
            flash('No group sales found within the selected date range.', 'error')
            return render_template('group_sales_reports.html', group_sales=group_sales)

    groups = Group.query.all()
    return render_template('group_sales_reports.html', group_sales=group_sales, groups=groups, start_date=start_date_str, end_date=end_date_str, group_id=group_id)

# 2. Route for predefined Group Sales Reports (Today, Month, Year)
@groups_bp.route("/group-sales-reports/predefined/<string:range_type>", methods=['GET'])
@login_required
def group_sales_reports_predefined(range_type):
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

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
        return redirect(url_for('groups.group_sales_reports'))

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    group_sales = GroupSale.query.filter(
        func.date(GroupSale.date) >= start_date_str,
        func.date(GroupSale.date) <= end_date_str
    ).all()

    groups = Group.query.all()
    return render_template('group_sales_reports.html', group_sales=group_sales, groups=groups, start_date=start_date_str, end_date=end_date_str, range_type=range_type)

# 3. Route for Group Management
@groups_bp.route('/group-management', methods=['GET'])
@login_required
def group_management():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    groups = Group.query.all()
    return render_template('group_management.html', groups=groups, role=current_user.role)

# 4. Route to create a new group
@groups_bp.route('/groups/create', methods=['POST'])
@login_required
def create_group():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    name = request.form.get('name')
    if not name:
        flash('Group name is required!', 'error')
        return redirect(url_for('groups.group_management'))

    new_group = Group(name=name)
    db.session.add(new_group)
    db.session.commit()

    flash(f'Group "{name}" created successfully!', 'success')
    return redirect(url_for('groups.group_management'))

# 5. Route to edit a group
@groups_bp.route('/groups/edit/<int:group_id>', methods=['POST'])
@login_required
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)
    if request.method == 'POST':
        group.name = request.form.get('name')
        db.session.commit()
        flash(f'Group "{group.name}" updated successfully.', 'success')
    return redirect(url_for('groups.group_management'))

# 6. Route to delete a group
@groups_bp.route('/groups/delete/<int:group_id>', methods=['POST'])
@login_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)

    db.session.delete(group)
    db.session.commit()

    flash(f'Group "{group.name}" deleted successfully.', 'success')
    return redirect(url_for('groups.group_management'))

# 7. Route to update group payment
@groups_bp.route('/groups/payment/<int:group_id>', methods=['POST'])
@login_required
def settle_group_payment(group_id):
    group = Group.query.get_or_404(group_id)
    payment = float(request.form.get('payment'))

    group.total_paid += payment
    group.total_due -= payment
    current_time_uae = datetime.now(pytz.timezone("Asia/Dubai"))

    new_payment = GroupPayment(group_id=group.id, amount_paid=payment, date_paid=current_time_uae)
    db.session.add(new_payment)
    db.session.commit()

    flash(f"Payment of {payment} settled for group {group.name}.", 'success')
    return redirect(url_for('groups.group_management'))

# 8. Route for Group Payment History
@groups_bp.route("/group/payment-history/<int:group_id>", methods=['GET'])
@login_required
def group_payment_history(group_id):
    group = Group.query.get_or_404(group_id)
    payments = GroupPayment.query.filter_by(group_id=group_id).all()
    return render_template('group_payment_history.html', group=group, payments=payments)

# 9. Route to download Group Sales Report as CSV
@groups_bp.route("/download-group-sales-report", methods=['GET'])
@login_required
def download_group_sales_report():
    if current_user.role not in ['admin', 'manager']:
        return redirect(url_for('auth.dashboard'))

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    group_id = request.args.get('group_id')

    try:
        datetime.strptime(start_date_str, '%Y-%m-%d')
        datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('groups.group_sales_reports'))

    query = GroupSale.query.filter(
        func.date(GroupSale.date) >= start_date_str.strip(),
        func.date(GroupSale.date) <= end_date_str.strip()
    )
    if group_id:
        query = query.filter(GroupSale.group_id == group_id)

    group_sales = query.all()

    if not group_sales:
        flash('No group sales found to generate the report.', 'error')
        return redirect(url_for('groups.group_sales_reports'))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Invoice Number', 'Date', 'Time', 'Group', 'Items', 'Subtotal', 'Tax', 'Discount', 'Grand Total', 'Served By', 'Payment Method', 'Notes'])

    for sale in group_sales:
        items = json.loads(sale.items)
        items_str = ', '.join([f"{item['name']} (Qty: {item.get('qty', 1)})" for item in items])
        writer.writerow([sale.invoice_number, sale.date, sale.time, sale.group.name, items_str, sale.subtotal, sale.tax, sale.discount, sale.grand_total, sale.server, sale.payment_method, sale.notes])

    output.seek(0)

    return Response(output, mimetype='text/csv', headers={'Content-Disposition': f'attachment;filename=group_sales_report_{start_date_str}_to_{end_date_str}.csv'})

# 10. Route to download Group Payment History as CSV
@groups_bp.route("/group/payment-history/download/<int:group_id>", methods=['GET'])
@login_required
def download_group_payment_history(group_id):
    group = Group.query.get_or_404(group_id)
    payments = GroupPayment.query.filter_by(group_id=group_id).all()

    output = io.StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow([f'Payment History for {group.name}'])
    csv_writer.writerow([])  # Empty row for spacing
    csv_writer.writerow(['Payment Amount', 'Date Paid'])

    for payment in payments:
        csv_writer.writerow([payment.amount_paid, payment.date_paid.strftime('%Y-%m-%d %H:%M:%S')])

    output.seek(0)

    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={group.name}_payment_history.csv"})

# 11. Route to reset the total paid amount to zero
@groups_bp.route('/groups/reset-paid/<int:group_id>', methods=['POST'])
@login_required
def reset_total_paid(group_id):
    if current_user.role not in ['admin']:
        return redirect(url_for('auth.dashboard'))

    group = Group.query.get_or_404(group_id)
    group.total_paid = 0.0
    group.total_due = 0.0
    db.session.commit()

    flash(f"Total paid amount for group {group.name} has been reset to zero.", 'success')
    return redirect(url_for('groups.group_management'))

# 12. Route to delete a group sale
@groups_bp.route('/delete-group-sale/<int:group_sale_id>', methods=['POST'])
@login_required
def delete_group_sale(group_sale_id):
    if current_user.role not in ['admin']:
        return redirect(url_for('auth.dashboard'))

    group_sale = GroupSale.query.get_or_404(group_sale_id)
    db.session.delete(group_sale)
    db.session.commit()

    flash('Group sale deleted successfully!', 'success')
    return redirect(url_for('groups.group_sales_reports'))

# 13. Route to get Group Sale data for download
@groups_bp.route("/get-group-sale/<int:group_sale_id>", methods=['GET'])
@login_required
def get_group_sale(group_sale_id):
    group_sale = GroupSale.query.get_or_404(group_sale_id)
    items = json.loads(group_sale.items)

    sale_data = {
        "invoice_number": group_sale.invoice_number,
        "date": group_sale.date,
        "time": group_sale.time,
        "items": items,
        "subtotal": group_sale.subtotal,
        "tax": group_sale.tax,
        "discount": group_sale.discount,
        "grand_total": group_sale.grand_total,
        "server": group_sale.server,
        "payment_method": group_sale.payment_method,
        "notes": group_sale.notes
    }

    return jsonify(sale_data)
