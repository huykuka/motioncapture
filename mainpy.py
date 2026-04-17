import sys
import os
import asyncio
import signal

if sys.platform == "win32":
    os.environ["PYTHONNET_INITIALIZE"] = "0"
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import threading
from imuclient import IMUClient
from cameraclient import CameraClient

imu = IMUClient()
cam = CameraClient()

# Hard kill on second Ctrl+C
signal.signal(signal.SIGINT, lambda *_: os._exit(1))


async def shutdown():
    """Stop data collection, disconnect BLE, shut down camera."""
    print("\nShutting down...")
    try:
        await imu.send_stop()
    except Exception:
        pass
    try:
        await imu.stop()
    except Exception:
        pass


async def main():
    cam_thread = threading.Thread(target=cam.run)
    cam_thread.start()

    await imu.start()

    print("READY (type start / stop / exit)")

    try:
        while True:
            cmd = await asyncio.get_event_loop().run_in_executor(None, input)
            cmd = cmd.strip().lower()

            if cmd == "start":
                print("SYSTEM START")
                await imu.send_start()
                cam.start()

            elif cmd == "stop":
                print("SYSTEM STOP")
                await imu.send_stop()
                cam.stop()

            elif cmd == "exit":
                break

    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        try:
            await asyncio.wait_for(shutdown(), timeout=5)
        except (asyncio.TimeoutError, Exception):
            pass
        cam.shutdown()
        cam_thread.join(timeout=3)
        print("Bye")
        os._exit(0)


asyncio.run(main())