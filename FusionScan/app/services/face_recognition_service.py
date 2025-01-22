import face_recognition
import cv2
import numpy as np
from app import db
from app.models import User
import os
import pickle  # Use pickle for serialization
from flask import current_app

def load_known_faces():
    with current_app.app_context():
        known_users = User.query.all()
        known_face_encodings = []
        known_face_names = []
        for user in known_users:
            if user.face_encodings:
                try:
                    # Load face encodings using pickle
                    encodings = pickle.loads(user.face_encodings)
                    known_face_encodings.extend(encodings)
                    known_face_names.extend([user.username] * len(encodings))
                except (pickle.UnpicklingError, TypeError) as e:
                    print(f"Error loading face encodings for user {user.username}: {e}")
                    print(f"Problematic data: {user.face_encodings}")  # Print for debugging
        return known_face_encodings, known_face_names

def facial_recognition_process(known_face_encodings, known_face_names):
    # Get a reference to the webcam
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        print("Error: Could not open video capture.")
        return None, "Unknown"

    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True

    while True:
        # Grab a single frame of video
        ret, frame = video_capture.read()
        if not ret:
            print("Error: Could not read frame from video stream.")
            break

        # Only process every other frame of video to save time
        if process_this_frame:
            # Resize frame of video to 1/4 size for faster face recognition processing
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
                face_id = None

                # Use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                if face_distances is not None and len(face_distances) > 0:
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]
                        # Assuming you have a way to get user_id from known_face_names
                        with current_app.app_context():
                            user = User.query.filter_by(username=name).first()
                            if user:
                                face_id = user.id

                face_names.append(name)
                if face_id is not None:
                    # If a match is found, return immediately
                    video_capture.release()
                    cv2.destroyAllWindows()
                    return face_id, name

        process_this_frame = not process_this_frame

        # Hit 'q' on the keyboard to quit!
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release handle to the webcam
    video_capture.release()
    cv2.destroyAllWindows()
    return None, "Unknown"

def capture_and_store_face_encodings(user_id):
    video_capture = cv2.VideoCapture(1)
    if not video_capture.isOpened():
        print("Error: Could not open video capture for capturing face encodings.")
        return

    face_encodings = []
    capture_count = 0
    max_captures = 5

    while capture_count < max_captures:
        ret, frame = video_capture.read()
        if not ret:
            print("Error: Could not read frame from video stream.")
            break

        # Display instructions on the frame
        instructions = f"Capturing face: {capture_count + 1}/{max_captures}"
        cv2.putText(frame, instructions, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv2.imshow('Video', frame)
        cv2.waitKey(1000)  # Wait for 1 second

        # Find face locations and encodings in the captured frame
        face_locations = face_recognition.face_locations(frame)
        if face_locations:
            # Use face_recognition.face_encodings directly
            new_encodings = face_recognition.face_encodings(frame, face_locations)
            if new_encodings:
                encoding = new_encodings[0]  # Take the first encoding if multiple faces are detected
                face_encodings.append(encoding)  # Store the encoding as is (no need to convert to list)
                capture_count += 1
        else:
            print(f"No face detected in frame {capture_count + 1}")

    video_capture.release()
    cv2.destroyAllWindows()

    if len(face_encodings) == max_captures:
        with current_app.app_context():
            user = User.query.get(user_id)
            # Serialize the face encodings using pickle
            user.face_encodings = pickle.dumps(face_encodings)
            db.session.commit()
    else:
        print("Failed to capture enough face encodings.")

def recognize_and_record_attendance(video_capture, known_face_encodings, known_user_ids):
    while True:
        ret, frame = video_capture.read()
        if not ret:
            break

        # Find face locations and encodings in the captured frame
        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"

            # If a match was found in known_face_encodings, use the first one
            if True in matches:
                first_match_index = matches.index(True)
                user_id = known_user_ids[first_match_index]
                user = User.query.get(user_id)
                name = user.name

                # Record attendance
                with current_app.app_context():
                    # Assuming you have an Attendance model to record attendance
                    attendance = attendance(user_id=user.id)
                    db.session.add(attendance)
                    db.session.commit()

            # Display the name on the frame
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.imshow('Video', frame)

        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()

# Example usage
video_capture = cv2.VideoCapture(0)
known_face_encodings = []  # Load known face encodings from your database
known_user_ids = []  # Load corresponding user IDs from your database
recognize_and_record_attendance(video_capture, known_face_encodings, known_user_ids)