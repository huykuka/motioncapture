import asyncio
import struct
import csv
import time
import cv2
import mediapipe as mp
import pandas as pd
from bleak import BleakScanner, BleakClient

# ==============================
# CONFIG
# ==============================

DEVICE_NAME = "Nano33BLE"
CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"

CAMERA_FPS = 30
IMU_RATE = 100

IMU_FILE = "imu_data.csv"
CAMERA_FILE = "camera_data.csv"
MERGED_FILE = "merged_motion_data.csv"

# ==============================
# FILE SETUP
# ==============================

imu_file = open(IMU_FILE, "w", newline="")
imu_writer = csv.writer(imu_file)

imu_writer.writerow([
    "pc_time",
    "arduino_time",
    "ax","ay","az",
    "gx","gy","gz"
])

cam_file = open(CAMERA_FILE, "w", newline="")
cam_writer = csv.writer(cam_file)

cam_writer.writerow([
    "frame", "timestamp",
    "shoulder_x","shoulder_y","shoulder_z","shoulder_visibility",
    "elbow_x","elbow_y","elbow_z","elbow_visibility",
    "wrist_x","wrist_y","wrist_z","wrist_visibility"
])

# ==============================
# MEDIAPIPE SETUP
# ==============================

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(0)

# ==============================
# GLOBAL VARIABLES
# ==============================

collecting = False
frame_count = 0
camera_interval = 1 / CAMERA_FPS
last_frame_time = 0

# ==============================
# BLE NOTIFICATION HANDLER
# ==============================

def notification_handler(sender, data):

    global collecting

    if not collecting:
        return

    pc_time = time.perf_counter()

    timestamp, ax, ay, az, gx, gy, gz = struct.unpack("I6f", data)

    imu_writer.writerow([
        pc_time,
        timestamp,
        ax, ay, az,
        gx, gy, gz
    ])

# ==============================
# CAMERA CAPTURE
# ==============================

def capture_camera():

    global frame_count, last_frame_time

    now = time.perf_counter()

    if now - last_frame_time < camera_interval:
        return

    last_frame_time = now

    ret, frame = cap.read()
    if not ret:
        return

    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image)

    if results.pose_landmarks:

        landmarks = results.pose_landmarks.landmark

        shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
        wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]

        cam_writer.writerow([
            frame_count, now,
            shoulder.x, shoulder.y, shoulder.z, shoulder.visibility,
            elbow.x, elbow.y, elbow.z, elbow.visibility,
            wrist.x, wrist.y, wrist.z, wrist.visibility
        ])

        frame_count += 1

    cv2.imshow("Camera Capture", frame)

# ==============================
# DATA MERGE FUNCTION
# ==============================

def merge_datasets():

    print("Loading CSV files...")

    imu = pd.read_csv(IMU_FILE)
    cam = pd.read_csv(CAMERA_FILE)

    imu = imu.sort_values("pc_time")
    cam = cam.sort_values("timestamp")

    print("Merging datasets...")

    merged = pd.merge_asof(
        cam,
        imu,
        left_on="timestamp",
        right_on="pc_time",
        direction="nearest"
    )

    merged.to_csv(MERGED_FILE, index=False)

    print("Merged dataset saved as:", MERGED_FILE)

# ==============================
# MAIN PROGRAM
# ==============================

async def main():

    global collecting

    print("Scanning BLE devices...")

    devices = await BleakScanner.discover()

    address = None

    for d in devices:
        if d.name == DEVICE_NAME:
            address = d.address

    if address is None:
        print("Arduino not found")
        return

    print("Connecting to Arduino...")

    async with BleakClient(address) as client:

        print("Connected!")

        await client.start_notify(CHAR_UUID, notification_handler)

        print("Type START to begin data collection")

        cmd = input()

        if cmd.lower() == "start":

            collecting = True

            await client.write_gatt_char(
                CHAR_UUID,
                b"START"
            )

            print("Collecting data... Press Q to stop")

        while True:

            if collecting:
                capture_camera()

            await asyncio.sleep(0.001)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    imu_file.close()
    cam_file.close()
    cv2.destroyAllWindows()

    print("Data collection finished")

    merge = input("Merge datasets now? (y/n): ")

    if merge.lower() == "y":
        merge_datasets()

asyncio.run(main())