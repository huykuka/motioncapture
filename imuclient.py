import asyncio
import struct
import csv
import time
from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Nano33BLE"  # Device name (more stable than address)
ADDRESS = "FB:5E:F5:A6:04:CB"  # Fallback address

IMU_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
CMD_UUID = "19B10002-E8F2-537E-4F6C-D104768A1214"

class IMUClient:

    def __init__(self):
        self.collecting = False
        self.file = open("imu_data.csv", "w", newline="")
        self.writer = csv.writer(self.file)

        self.writer.writerow([
            "pc_time","arduino_time",
            "ax","ay","az","gx","gy","gz"
        ])

    def handler(self, sender, data):

        if not self.collecting:
            return

        pc_time = time.perf_counter()
        timestamp, ax, ay, az, gx, gy, gz = struct.unpack("I6f", data)

        self.writer.writerow([
            pc_time, timestamp,
            ax, ay, az, gx, gy, gz
        ])

    async def start(self):
        # Scan for BLE devices
        print("Scanning for BLE devices...")
        devices = await BleakScanner.discover()
        
        device = None
        
        # First, try to match by device name (more stable)
        for d in devices:
            print(f"Found: {d.address} - {d.name}")
            if d.name == DEVICE_NAME:
                device = d
                break
        
        # Fallback: try to match by address
        if device is None:
            for d in devices:
                if d.address == ADDRESS:
                    device = d
                    break
        
        if device is None:
            print(f"Device '{DEVICE_NAME}' not found!")
            return
        
        print(f"Connecting to {device.name} ({device.address})...")
        self.client = BleakClient(device)
        await self.client.connect()

        print("IMU connected")

        await self.client.start_notify(IMU_UUID, self.handler)

    async def send_start(self):
        self.collecting = True
        await self.client.write_gatt_char(CMD_UUID, b"START")

    async def send_stop(self):
        self.collecting = False
        await self.client.write_gatt_char(CMD_UUID, b"STOP")

    async def stop(self):
        await self.client.disconnect()
        self.file.close()