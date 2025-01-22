from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Check if an admin user already exists
    admin_exists = User.query.filter_by(is_admin=True).first()
    if admin_exists:
        print("An admin user already exists.")
    else:
        # Create a new admin user
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('iloveuzneb'),  # Replace 'admin_password' with a strong password
            is_admin=True,
            student_lrn='N/A',  # You can set appropriate values here
            strand='N/A'
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created successfully.")