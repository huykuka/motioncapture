import asyncio
import struct
import csv
import time
from bleak import BleakClient

ADDRESS = "FB:5E:F5:A6:04:CB"  # sửa đúng address

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

        self.client = BleakClient(ADDRESS)
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