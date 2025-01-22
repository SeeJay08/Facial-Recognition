from app import db
from app.models import User, Attendance
from datetime import datetime
from flask import current_app

def record_attendance(user_id, temperature, status):
    with current_app.app_context():
        attendance = Attendance(user_id=user_id, temperature=temperature, status=status)
        db.session.add(attendance)
        db.session.commit()

def get_user_by_id(user_id):
    with current_app.app_context():
        return User.query.get(user_id)

def delete_user_by_id(user_id):
    with current_app.app_context():
        user = User.query.get(user_id)
        if user:
            # Delete associated attendance records first
            Attendance.query.filter_by(user_id=user_id).delete()
            # Then delete the user
            db.session.delete(user)
            db.session.commit()
            return True
        return False