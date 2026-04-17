
import struct
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import csv
import time
import cv2
import mediapipe as mp
from bleak import BleakClient, BleakScanner

# ==============================
# CONFIG
# ==============================

DEVICE_NAME = "Nano33BLE"  # Connect by name instead of address
IMU_SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214"  # From your Arduino code
IMU_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
CMD_UUID = "19B10002-E8F2-537E-4F6C-D104768A1214"

CAMERA_FPS = 30

# ==============================
# FILE SETUP
# ==============================

imu_file = open("imu_data.csv", "w", newline="")
imu_writer = csv.writer(imu_file)

imu_writer.writerow([
    "pc_time","arduino_time",
    "ax","ay","az","gx","gy","gz"
])

cam_file = open("camera_data.csv", "w", newline="")
cam_writer = csv.writer(cam_file)

cam_writer.writerow([
    "frame","timestamp",
    "shoulder_x","shoulder_y","shoulder_z","shoulder_visibility",
    "elbow_x","elbow_y","elbow_z","elbow_visibility",
    "wrist_x","wrist_y","wrist_z","wrist_visibility"
])

# ==============================
# MEDIAPIPE
# ==============================

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

# ==============================
# GLOBAL
# ==============================

collecting = False
frame_count = 0
camera_interval = 1 / CAMERA_FPS
last_frame_time = 0

cap = None

# ==============================
# IMU HANDLER
# ==============================

def imu_handler(sender, data):

    if not collecting:
        return

    pc_time = time.perf_counter()

    timestamp, ax, ay, az, gx, gy, gz = struct.unpack("I6f", data)

    imu_writer.writerow([
        pc_time, timestamp,
        ax, ay, az,
        gx, gy, gz
    ])

# ==============================
# CAMERA TASK
# ==============================

async def camera_task():

    global frame_count, last_frame_time

    while True:

        if collecting:
            now = time.perf_counter()

            if now - last_frame_time >= camera_interval:

                last_frame_time = now

                ret, frame = cap.read()
                if not ret:
                    continue

                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(image)

                if results.pose_landmarks:

                    lm = results.pose_landmarks.landmark

                    shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]
                    elbow = lm[mp_pose.PoseLandmark.RIGHT_ELBOW]
                    wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST]

                    cam_writer.writerow([
                        frame_count, now,
                        shoulder.x, shoulder.y, shoulder.z, shoulder.visibility,
                        elbow.x, elbow.y, elbow.z, elbow.visibility,
                        wrist.x, wrist.y, wrist.z, wrist.visibility
                    ])

                    frame_count += 1

                cv2.imshow("Camera", frame)

        await asyncio.sleep(0)

# ==============================
# MAIN
# ==============================

async def main():

    global collecting, cap

    # Check for device address from config or user input
    device_address = None
    
    # Look for config file first
    import os
    config_file = "arduino_address.txt"
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            device_address = f.read().strip()
        print(f"Using saved address from {config_file}: {device_address}")
    
    if not device_address:
        print("\n=== Arduino Device Discovery ===")
        print("Scanning for BLE devices...")
        devices = await BleakScanner.discover(timeout=5.0)

        print(f"\nFound {len(devices)} devices:")
        for i, d in enumerate(devices):
            name = d.name if d.name else "(no name)"
            print(f"  {i}: {name:30} {d.address}")
        
        print("\nOptions:")
        print("  1. Enter device number from list above")
        print("  2. Enter MAC address manually (AA:BB:CC:DD:EE:FF)")
        print("  3. Type 'skip' to try simple_ble_collect.py instead")
        
        user_input = input("\nEnter choice: ").strip()
        
        if user_input.lower() == "skip":
            print("\nuse: python simple_ble_collect.py")
            return
        
        # Check if it's a number
        try:
            idx = int(user_input)
            if 0 <= idx < len(devices):
                device_address = devices[idx].address
                print(f"Selected: {device_address}")
                # Save for next time
                with open(config_file, "w") as f:
                    f.write(device_address)
            else:
                print("Invalid device number")
                return
        except ValueError:
            # Assume it's a MAC address
            if ":" in user_input and len(user_input) == 17:
                device_address = user_input
                print(f"Using address: {device_address}")
                with open(config_file, "w") as f:
                    f.write(device_address)
            else:
                print("Invalid input")
                return

    print(f"\nConnecting to {device_address}...")

    try:
        async with BleakClient(device_address, timeout=20.0) as client:

            print("✓ Connected!")

            cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                print("Camera error")
                return

            await client.start_notify(IMU_UUID, imu_handler)

            asyncio.create_task(camera_task())

            while True:

                cmd = input("\nSTART / STOP / EXIT: ").lower()

                if cmd == "start":
                    collecting = True
                    await client.write_gatt_char(CMD_UUID, b"START")
                    print("Recording...")

                elif cmd == "stop":
                    collecting = False
                    await client.write_gatt_char(CMD_UUID, b"STOP")
                    print("Stopped")

                elif cmd == "exit":
                    break

            cap.release()
            imu_file.close()
            cam_file.close()
            cv2.destroyAllWindows()

            print("Done!")
    
    except Exception as e:
        print(f"✗ Connection failed: {type(e).__name__}: {e}")
        print("\nDelete arduino_address.txt and try again to re-select device")
        raise

# ==============================
# SETUP for Windows Bleak
# ==============================

if sys.platform == "win32":
    try:
        from bleak.backends.winrt.util import allow_sta
        allow_sta()
    except ImportError:
        pass

asyncio.run(main())