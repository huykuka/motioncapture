import sys
import asyncio

if sys.platform == "win32":
    import os
    os.environ["PYTHONNET_INITIALIZE"] = "0"
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import threading
from imuclient import IMUClient
from cameraclient import CameraClient

imu = IMUClient()
cam = CameraClient()

async def main():

    await imu.start()

    print("READY (type start / stop / exit)")

    # 🔥 chạy camera thread 1 lần duy nhất
    cam_thread = threading.Thread(target=cam.run)
    cam_thread.start()

    while True:

        cmd = input().lower()

        if cmd == "start":

            print("SYSTEM START")

            await imu.send_start()
            cam.start()

        elif cmd == "stop":

            print("SYSTEM STOP")

            await imu.send_stop()
            cam.stop()

        elif cmd == "exit":

            print("SYSTEM EXIT")

            await imu.stop()
            cam.shutdown()

            cam_thread.join()
            break

asyncio.run(main())