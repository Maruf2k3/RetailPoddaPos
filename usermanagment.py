from flask import Blueprint, render_template , redirect , url_for , request , flash
from flask_login import login_required,current_user
from models import User, db
from flask_wtf.csrf import CSRFProtect

usermanagment_bp = Blueprint('usermanagment', __name__)



csrf = CSRFProtect()

@usermanagment_bp.route("/user-management", methods=['GET', 'POST'])
@login_required
@csrf.exempt  # Disable CSRF protection for this route
def user_management():
    if current_user.role != 'admin':
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')

        if action == 'edit':
            user = User.query.get(user_id)
            if not user:
                flash('User not found!', 'error')
                return redirect(url_for('auth.user_management'))

            # Update role
            user.role = request.form.get('role')

            # Update password if provided
            password = request.form.get('password')
            if password:
                user.set_password(password)

            db.session.commit()
            flash('User updated successfully!', 'success')

        elif action == 'delete':
            user = User.query.get(user_id)
            if not user:
                flash('User not found!', 'error')
                return redirect(url_for('auth.user_management'))

            db.session.delete(user)
            db.session.commit()
            flash('User deleted successfully!', 'success')

    # Fetch users for display
    users = User.query.all()
    return render_template('user_management.html', users=users)