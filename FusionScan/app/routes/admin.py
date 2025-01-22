from flask import Blueprint, render_template, redirect, url_for, flash, request
from app import db
from app.models import User
from app.utils.decorators import admin_required
from app.services.data_service import delete_user_by_id
from app.services.face_recognition_service import capture_and_store_face_encodings
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        student_lrn = request.form.get('student_lrn')
        strand = request.form.get('strand')

        if not username or not email or not password or not student_lrn or not strand:
            flash('Please fill in all fields.', 'danger')
            return redirect(url_for('admin.add_user'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('admin.add_user'))

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            student_lrn=student_lrn,
            strand=strand
        )
        db.session.add(new_user)
        db.session.commit()

        capture_and_store_face_encodings(new_user.id)

        flash(f'User {username} added successfully!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/add_user.html')

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if delete_user_by_id(user_id):
        flash('User deleted successfully!', 'success')
    else:
        flash('Error deleting user.', 'danger')
    return redirect(url_for('admin.dashboard'))