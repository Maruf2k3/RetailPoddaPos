from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from models import db, Attendance, Employee
from datetime import datetime
import pytz

attendance_bp = Blueprint('attendance', __name__)

# Clock-In route for Attendance
@attendance_bp.route("/employee/clock-in/<int:employee_id>", methods=["POST"])
@login_required
def clock_in(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    clock_in_time = datetime.now(pytz.timezone("Asia/Dubai"))

    attendance = Attendance(employee_id=employee.id, clock_in=clock_in_time)
    db.session.add(attendance)
    db.session.commit()

    flash(f'{employee.name} clocked in successfully!', 'success')
    return redirect(url_for('employees.employee_dashboard'))

# Clock-Out route for Attendance
@attendance_bp.route("/employee/clock-out/<int:employee_id>", methods=["POST"])
@login_required
def clock_out(employee_id):
    attendance = Attendance.query.filter_by(employee_id=employee_id, clock_out=None).first()
    if attendance:
        attendance.clock_out = datetime.now(pytz.timezone("Asia/Dubai"))
        db.session.commit()
        flash(f'{attendance.employee.name} clocked out successfully!', 'success')
    else:
        flash('No clock-in record found for this employee.', 'error')
    return redirect(url_for('employees.employee_dashboard'))

# Employee Profile View with Attendance Records
@attendance_bp.route("/employee/profile/<int:employee_id>", methods=["GET"])
@login_required
def employee_profile(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    attendance_records = Attendance.query.filter_by(employee_id=employee_id).all()
    return render_template('employee_profile.html', employee=employee, attendance_records=attendance_records)
