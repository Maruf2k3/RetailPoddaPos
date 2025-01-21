from flask import Blueprint, request, render_template, jsonify
from flask_login import current_user, login_required
from datetime import datetime
import json
import pytz
import uuid

from models import db, Order, MenuItem, Sale  # Ensure we import Sale here

ordermanagement = Blueprint('ordermanagement', __name__)

def merge_order_items(json_str):
    """
    Merge items with the same (name, price).
    Ignores served_by when combining quantities.
    """
    try:
        items_list = json.loads(json_str)
    except (ValueError, TypeError):
        return json_str  # If parsing fails, just return original string

    merged = {}
    for item in items_list:
        name = item.get("name", "")
        price = float(item.get("price", 0.0))
        qty = int(item.get("qty", 1))

        # Merge key = (name, price), ignoring served_by
        key = (name, price)
        if key not in merged:
            merged[key] = {
                "name": name,
                "price": price,
                "qty": 0
                # served_by is ignored here for merging
            }
        merged[key]["qty"] += qty

    merged_list = list(merged.values())
    return json.dumps(merged_list)

@ordermanagement.route('/order-management', methods=['GET'])
@login_required
def order_management():
    sort_param = request.args.get('sort', 'desc')
    if sort_param == 'asc':
        orders = Order.query.order_by(Order.table_number.asc()).all()
    else:
        orders = Order.query.order_by(Order.table_number.desc()).all()

    menu_items = MenuItem.query.all()
    unique_categories = sorted({item.category for item in menu_items if item.category})

    return render_template(
        'ordermanagement.html',
        orders=orders,
        menu_items=menu_items,
        unique_categories=unique_categories,
        name=current_user.username,
        role=current_user.role,
        sort=sort_param
    )

@ordermanagement.route('/order/<int:order_id>', methods=['GET'])
@login_required
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify({
        "id": order.id,
        "table_number": order.table_number,
        "notes": order.notes or "",
        "items": json.loads(order.items),
        "subtotal": order.subtotal,
        "tax": order.tax,
        "grand_total": order.grand_total,
        "amount_paid": order.amount_paid,
        "status": order.status,
    })

@ordermanagement.route('/order/save', methods=['POST'])
@login_required
def save_order():
    data = request.json
    if data.get("order_id"):
        order = Order.query.get_or_404(data["order_id"])
    else:
        order = Order()
        order.created_at = datetime.now()
        order.created_by = current_user.username
        order.status = "Unpaid"
        order.amount_paid = 0.0

    order.table_number = int(data["table_number"])
    order.notes = data.get("notes", "")
    order.items = json.dumps(data["items"])
    order.subtotal = data["subtotal"]
    order.tax = data["tax"]
    order.grand_total = data["grand_total"]

    db.session.add(order)
    db.session.commit()
    return '', 200

@ordermanagement.route('/order/settle/<int:order_id>', methods=['POST'])
@login_required
def settle_order(order_id):
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'message': 'Unauthorized'}), 403

    order = Order.query.get_or_404(order_id)

    # If toggling from Paid -> Unpaid
    if order.status == "Paid":
        order.status = "Unpaid"
        order.amount_paid = 0.0
        if order.sale_id:
            sale_to_delete = Sale.query.get(order.sale_id)
            if sale_to_delete:
                db.session.delete(sale_to_delete)
            order.sale_id = None
    else:
        # Unpaid -> Paid
        order.status = "Paid"
        order.amount_paid = order.grand_total
        if not order.sale_id:
            current_time_uae = datetime.now(pytz.timezone("Asia/Dubai"))
            merged_items_json = merge_order_items(order.items)
            new_sale = Sale(
                invoice_number=str(uuid.uuid4()),
                date=current_time_uae.strftime("%Y-%m-%d"),
                time=current_time_uae.strftime("%H:%M:%S"),
                items=merged_items_json,
                subtotal=order.subtotal,
                tax=order.tax,
                grand_total=order.grand_total,
                discount=0.0,
                notes=order.notes or "",
                server=order.created_by,
                customer_id=None,
                payment_method="cash"
            )
            db.session.add(new_sale)
            db.session.flush()
            order.sale_id = new_sale.id

    db.session.commit()
    return '', 200

@ordermanagement.route('/order/pay/<int:order_id>', methods=['POST'])
@login_required
def partial_payment(order_id):
    if current_user.role not in ['admin', 'manager', 'staff']:
        return jsonify({'message': 'Unauthorized'}), 403

    order = Order.query.get_or_404(order_id)
    data = request.json or {}
    payment_amount = data.get("payment_amount", 0.0)

    if payment_amount <= 0:
        return jsonify({'message': 'Invalid payment amount.'}), 400
    if order.amount_paid >= order.grand_total:
        return jsonify({'message': 'Order is already fully paid.'}), 400

    order.amount_paid += payment_amount
    if order.amount_paid >= order.grand_total:
        order.amount_paid = order.grand_total
        order.status = "Paid"

        if not order.sale_id:
            current_time_uae = datetime.now(pytz.timezone("Asia/Dubai"))
            merged_items_json = merge_order_items(order.items)
            new_sale = Sale(
                invoice_number=str(uuid.uuid4()),
                date=current_time_uae.strftime("%Y-%m-%d"),
                time=current_time_uae.strftime("%H:%M:%S"),
                items=merged_items_json,
                subtotal=order.subtotal,
                tax=order.tax,
                grand_total=order.grand_total,
                discount=0.0,
                notes=order.notes or "",
                server=order.created_by,
                customer_id=None,
                payment_method="cash"
            )
            db.session.add(new_sale)
            db.session.flush()
            order.sale_id = new_sale.id

    elif order.amount_paid > 0:
        order.status = "Partially Paid"
    else:
        order.status = "Unpaid"

    db.session.commit()

    return jsonify({
        "order_id": order.id,
        "amount_paid": order.amount_paid,
        "grand_total": order.grand_total,
        "status": order.status
    }), 200

@ordermanagement.route('/order/delete/<int:order_id>', methods=['POST'])
@login_required
def delete_order(order_id):
    if current_user.role not in ['admin']:
        return jsonify({'message': 'Unauthorized'}), 403

    order = Order.query.get_or_404(order_id)
    if order.status != 'Paid':
        return jsonify({'message': 'Cannot delete unpaid orders.'}), 400

    if order.sale_id:
        sale_to_delete = Sale.query.get(order.sale_id)
        if sale_to_delete:
            db.session.delete(sale_to_delete)

    db.session.delete(order)
    db.session.commit()
    return '', 200

@ordermanagement.route('/orders/clear', methods=['POST'])
@login_required
def clear_all_orders():
    if current_user.role != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403

    paid_orders = Order.query.filter_by(status='Paid').all()
    for order in paid_orders:
        if order.sale_id:
            sale_to_delete = Sale.query.get(order.sale_id)
            if sale_to_delete:
                db.session.delete(sale_to_delete)
        db.session.delete(order)
    db.session.commit()

    return '', 200


@ordermanagement.route('/get-sale/<int:sale_id>', methods=['GET'])
@login_required
def get_sale(sale_id):
    from models import Sale  # or wherever your Sale model is defined
    sale = Sale.query.get_or_404(sale_id)
    
    # Convert items JSON to Python, then back to JSON for clarity
    items_data = json.loads(sale.items) if sale.items else []
    
    # Return the sale data
    return jsonify({
        "invoice_number": sale.invoice_number,
        "date": sale.date,
        "time": sale.time,
        "items": items_data,
        "subtotal": sale.subtotal,
        "tax": sale.tax,
        "discount": sale.discount,
        "grand_total": sale.grand_total,
        "notes": sale.notes,
        "server": sale.server,
        # If you actually have a customer name in your DB. If not, you can remove or keep as ""
        "customer": getattr(sale, 'customer', '') or ""
    })
