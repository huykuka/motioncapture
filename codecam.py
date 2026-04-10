import cv2
import mediapipe as mp
import csv
import time

mp_pose = mp.solutions.pose
cap = cv2.VideoCapture(0)

file = open("arm_data_advanced.csv", mode='w', newline='') 
writer = csv.writer(file)

writer.writerow([
    "frame", "timestamp",
    "shoulder_x", "shoulder_y", "shoulder_z", "shoulder_visibility",
    "elbow_x", "elbow_y", "elbow_z", "elbow_visibility",
    "wrist_x", "wrist_y", "wrist_z", "wrist_visibility"
])

frame_count = 0
start_time = time.time()

with mp_pose.Pose(min_detection_confidence=0.5,
                  min_tracking_confidence=0.5) as pose:

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = time.time() - start_time

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]

            writer.writerow([
                frame_count, timestamp,
                shoulder.x, shoulder.y, shoulder.z, shoulder.visibility,
                elbow.x, elbow.y, elbow.z, elbow.visibility,
                wrist.x, wrist.y, wrist.z, wrist.visibility
            ])

            frame_count += 1

        cv2.imshow("Collecting Data", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
file.close()
cv2.destroyAllWindows()