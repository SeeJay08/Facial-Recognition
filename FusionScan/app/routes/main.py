from flask import Blueprint, render_template, flash, redirect, url_for, request, Response
from app.services.face_recognition_service import facial_recognition_process, load_known_faces
from app.services.data_service import record_attendance, get_user_by_id, delete_user_by_id
from flask_login import current_user, login_required
from app.models import User, Attendance
from datetime import datetime, date
import cv2
import face_recognition
import numpy as np
import pandas as pd
from app import db
import io
import csv

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        # Get all users and their attendance records for today
        users = User.query.all()
        today = date.today()
        for user in users:
            attendance_record = Attendance.query.filter_by(user_id=user.id).filter(Attendance.timestamp >= today).first()
            if attendance_record:
                user.attendance_status = attendance_record.status
                user.attendance_time = attendance_record.timestamp.strftime('%I:%M %p')
            else:
                user.attendance_status = 'Absent'
                user.attendance_time = ''

        return render_template('index.html', users=users)
    else:
        return render_template('index.html', users=None)

@main_bp.route('/scan', methods=['GET', 'POST'])
@login_required
def scan_student():
    known_face_encodings, known_face_names = load_known_faces()
    result = facial_recognition_process(known_face_encodings, known_face_names)
    if result is None:
        flash('Facial recognition process failed. Please try again.', 'danger')
        return redirect(url_for('main.index'))

    user_id, recognized_name = result

    if user_id:
        user = get_user_by_id(user_id)
        if not user:
            flash('User not found in the database.', 'danger')
            return redirect(url_for('main.index'))

        today = date.today()
        attendance_record = Attendance.query.filter_by(user_id=user.id).filter(Attendance.timestamp >= today).first()

        if attendance_record:
            flash('Attendance already recorded for today.', 'warning')
            return redirect(url_for('main.index'))
        else:
            status = "Present"
            record_attendance(user_id, None, status)
            flash(f'Welcome, {recognized_name}! Your attendance has been recorded.', 'success')
            return redirect(url_for('main.index'))
    else:
        status = "Unknown"
        record_attendance(None, None, status)
        flash('Face not recognized. Please try again or contact the administrator.', 'warning')
        return redirect(url_for('main.index'))

@main_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash('You do not have permission to delete users.', 'danger')
        return redirect(url_for('main.index'))

    if delete_user_by_id(user_id):
        flash(f'User and their attendance records have been deleted.', 'success')
    else:
        flash('Error deleting user.', 'danger')
    return redirect(url_for('main.index'))

def process_frame_for_recognition(frame, known_face_encodings, known_face_names):
    # Resize frame for faster processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    face_names = []
    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"

        # Use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        if face_distances is not None and len(face_distances) > 0:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_face_names[best_match_index]

        face_names.append(name)

    return face_locations, face_names

def generate_frames(known_face_encodings, known_face_names):
    video_capture = cv2.VideoCapture(1)

    if not video_capture.isOpened():
        print("Error: Could not open video capture.")
        return

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Error: Could not read frame from video stream.")
            break

        # Perform facial recognition on the frame
        face_locations, face_names = process_frame_for_recognition(frame, known_face_encodings, known_face_names)

        # Display the results
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations since the frame was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

        # Encode the frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        # Yield the frame for the video feed
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    video_capture.release()

@main_bp.route('/video_feed')
@login_required
def video_feed():
    known_face_encodings, known_face_names = load_known_faces()
    return Response(generate_frames(known_face_encodings, known_face_names), mimetype='multipart/x-mixed-replace; boundary=frame')

@main_bp.route('/restart_attendance', methods=['POST'])
@login_required
def restart_attendance():
    if not current_user.is_admin:
        flash('You do not have permission to restart attendance.', 'danger')
        return redirect(url_for('main.index'))

    try:
        # Get today's date
        today = date.today()

        # Delete all attendance records for today
        Attendance.query.filter(Attendance.timestamp >= today).delete()
        db.session.commit()
        flash('Attendance records for today have been cleared.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while clearing attendance: {e}', 'danger')

    return redirect(url_for('main.index'))

@main_bp.route('/export_attendance')
@login_required
def export_attendance():
    if not current_user.is_admin:
        flash('You do not have permission to export attendance.', 'danger')
        return redirect(url_for('main.index'))

    # Query attendance records (you might want to add filtering options here)
    attendance_records = Attendance.query.all()

    # Create a DataFrame
    data = []
    for record in attendance_records:
        user = User.query.get(record.user_id)
        if user:
            data.append([user.username, user.student_lrn, user.strand, record.status, record.timestamp.strftime('%Y-%m-%d %I:%M %p')])

    df = pd.DataFrame(data, columns=['Name', 'LRN', 'Strand', 'Status', 'Timestamp'])

    # Create a CSV in memory
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Attendance', index=False)
    writer.close()
    output.seek(0)

    return Response(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": "attachment;filename=attendance_records.xlsx"}
    )