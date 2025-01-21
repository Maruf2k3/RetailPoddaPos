import uuid
from pytz import timezone
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship

from app_init import db  # Ensure this is your correct db import


# For Super Users
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# For Menu
class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)


# For Bills (Sales)
class Sale(db.Model):
    __tablename__ = 'sales'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_number = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
        default=lambda: str(uuid.uuid4())
    )  # Unique Invoice Number
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    items = db.Column(db.Text, nullable=False)  # Store items as JSON
    subtotal = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=False)
    grand_total = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, nullable=True, default=0.0)
    notes = db.Column(db.String(255), nullable=True, default='')
    server = db.Column(db.String(100), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    payment_method = db.Column(db.String(50), nullable=False)

    # Relationship with Customer
    customer = db.relationship('Customer', back_populates='sales')
    # Relationship with Order (via backref in Order.sale)
    # Because of the line in Order:
    #   sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True)
    #   sale = relationship("Sale", backref="order", uselist=False)
    # The `Sale` can also access a single `Order` via `sale.order`.


# CRM
class Customer(db.Model):
    __tablename__ = 'customer'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)

    # Back reference to the Sale model
    sales = db.relationship('Sale', back_populates='customer')


# Groups
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    total_due = db.Column(db.Float, default=0.0)
    total_paid = db.Column(db.Float, default=0.0)

    # Relationship to track group payments
    payments = db.relationship('GroupPayment', backref='related_group', lazy=True)

    # Relationship to track group sales
    sales = db.relationship('GroupSale', backref='related_group', lazy=True)


class GroupSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
        default=lambda: str(uuid.uuid4())
    )
    date = db.Column(db.String(50), nullable=False)
    time = db.Column(db.String(50), nullable=False)
    items = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=False)
    grand_total = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, nullable=True, default=0.0)
    payment_method = db.Column(db.String(50), nullable=False)
    server = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.String(255), nullable=True, default='')

    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    group = db.relationship('Group', backref=db.backref('group_sales', lazy=True))


class GroupPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    date_paid = db.Column(db.DateTime)

    group = db.relationship('Group', backref=db.backref('group_payments', lazy=True))


# For Staff
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(100), nullable=False)

    # Attendance relationship
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False)
    clock_out = db.Column(db.DateTime, nullable=True)

    @property
    def worked_hours(self):
        if self.clock_out:
            worked_time = self.clock_out - self.clock_in
            total_minutes = int(worked_time.total_seconds() / 60)
            hours, minutes = divmod(total_minutes, 60)
            if hours > 0:
                return f"{hours} hour(s), {minutes} minute(s)"
            else:
                return f"{minutes} minute(s)"
        return None


class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(20), nullable=False)
    last_modified = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone("Asia/Dubai")),
        onupdate=lambda: datetime.now(timezone("Asia/Dubai"))
    )

    def add_quantity(self, amount):
        """Add quantity when new stock arrives."""
        self.quantity += amount

    def subtract_quantity(self, amount):
        """Subtract quantity when stock is used."""
        self.quantity -= amount if self.quantity >= amount else 0


class InventoryLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('inventory.id'), nullable=False)
    used_quantity = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    inventory_item = db.relationship('Inventory', backref='usage_logs')


class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    vendor = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # e.g., Maintenance, Ingredient
    date = db.Column(db.Date)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text, nullable=True)


# Updated Order model with sale_id & relationship
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.Integer, nullable=False)  # Changed to integer
    notes = db.Column(db.Text, nullable=True)             # New notes field
    items = db.Column(db.Text, nullable=False)            # JSON string for items
    subtotal = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=False)
    grand_total = db.Column(db.Float, nullable=False)

    amount_paid = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(50), default="Unpaid")
    created_at = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.String(50), nullable=False)

    # Link to the Sale model
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True)
    sale = relationship("Sale", backref="order", uselist=False)

    def __repr__(self):
        return f"<Order id={self.id}, table={self.table_number}, status={self.status}>"
