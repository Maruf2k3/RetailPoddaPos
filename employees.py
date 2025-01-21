from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Employee
from attendance import Attendance  # Ensure Attendance is imported if defined separately

employees_bp = Blueprint('employees', __name__)

# Employee Dashboard - Displays all employees and allows adding new employees
@employees_bp.route("/employees", methods=["GET", "POST"])
@login_required
def employee_dashboard():
    employees = Employee.query.all()
    for employee in employees:
        employee.clocked_in = Attendance.query.filter_by(employee_id=employee.id, clock_out=None).first() is not None

    if request.method == 'POST':
        name = request.form.get('name')
        position = request.form.get('position')
        contact_info = request.form.get('contact_info')

        new_employee = Employee(name=name, position=position, contact_info=contact_info)
        db.session.add(new_employee)
        db.session.commit()
        flash('Employee added successfully!', 'success')
        return redirect(url_for('employees.employee_dashboard'))

    return render_template('employee_dashboard.html', employees=employees)

# Add or Edit Employee
@employees_bp.route("/employee/add", methods=["POST"])
@employees_bp.route("/employee/edit/<int:employee_id>", methods=["GET", "POST"])
@login_required
def add_edit_employee(employee_id=None):
    employee = Employee.query.get(employee_id) if employee_id else None

    if request.method == "POST":
        name = request.form.get('name')
        position = request.form.get('position')
        contact_info = request.form.get('contact_info')

        if employee:
            employee.name = name
            employee.position = position
            employee.contact_info = contact_info
            flash('Employee updated successfully!', 'success')
        else:
            new_employee = Employee(name=name, position=position, contact_info=contact_info)
            db.session.add(new_employee)
            flash('Employee added successfully!', 'success')

        db.session.commit()
        return redirect(url_for('employees.employee_dashboard'))

    return render_template('employee_dashboard.html', employee=employee)

# Delete Employee
@employees_bp.route("/employee/delete/<int:employee_id>", methods=["POST"])
@login_required
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    db.session.delete(employee)
    db.session.commit()
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('employees.employee_dashboard'))
