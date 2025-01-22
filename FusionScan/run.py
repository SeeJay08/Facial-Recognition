from app import create_app, db
from app.services.face_recognition_service import load_known_faces

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)