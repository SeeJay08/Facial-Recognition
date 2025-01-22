from flask import Blueprint, render_template, redirect, url_for, flash
from app import db
from app.forms import LoginForm, RegistrationForm
from app.models import User
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, login_required
from app.services.face_recognition_service import capture_and_store_face_encodings

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('Login successful!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password_hash=hashed_password, student_lrn=form.student_lrn.data, strand=form.strand.data)
        db.session.add(user)
        db.session.commit()

        # Capture and store face encodings
        capture_and_store_face_encodings(user.id)

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))