import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        from bleak.backends.winrt.util import allow_sta
        allow_sta()
    except ImportError:
        pass

from bleak import BleakScanner, BleakClient

IMU_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
IMU_SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214"

async def diagnose():
    print("=" * 60)
    print("BLE DEVICE DIAGNOSTIC")
    print("=" * 60)
    
    print("\n[1/3] Scanning for devices (10 seconds)...")
    devices = await BleakScanner.discover(timeout=10.0)
    
    print(f"\nFound {len(devices)} devices:\n")
    for i, d in enumerate(devices):
        name = d.name if d.name else "(no name)"
        print(f"  [{i}] {name:25} {d.address}")
    
    print("\n" + "=" * 60)
    print("[2/3] Attempting to connect to each device...")
    print("=" * 60)
    
    for i, d in enumerate(devices):
        name = d.name if d.name else "(no name)"
        print(f"\n  [{i}] {name} ({d.address})")
        
        try:
            print(f"       Connecting (10s timeout)...", end="", flush=True)
            client = BleakClient(d.address, timeout=10.0)
            await client.connect()
            print(" ✓ Connected")
            
            # List services and characteristics
            print(f"       Services found: {len(client.services)}")
            
            found_imu_char = False
            found_imu_service = False
            
            for service in client.services:
                if service.uuid.lower() == IMU_SERVICE_UUID.lower():
                    found_imu_service = True
                    print(f"       ✓ Found IMU Service: {service.uuid}")
                    
                for char in service.characteristics:
                    if char.uuid.lower() == IMU_UUID.lower():
                        found_imu_char = True
                        print(f"         ✓ Found IMU Characteristic: {char.uuid}")
                        print(f"           Properties: {char.properties}")
            
            if found_imu_char:
                print(f"\n       *** THIS IS YOUR ARDUINO ***")
                print(f"       Address: {d.address}")
                return d.address
            
            await client.disconnect()
            print(f"       (Not the Arduino - no IMU characteristic)")
            
        except asyncio.TimeoutError:
            print(f" ✗ Timeout (device not responding)")
        except Exception as e:
            print(f" ✗ Error: {type(e).__name__}")
    
    print("\n" + "=" * 60)
    print("[3/3] RESULT")
    print("=" * 60)
    print("\n✗ Arduino not found among these devices")
    print("\nPossible solutions:")
    print("  1. Make sure Arduino is powered on")
    print("  2. Make sure it's NOT connected to your phone")
    print("  3. Add a small delay (100ms) in your Arduino code:")
    print("     delay(100); // after BLE.advertise()")
    print("  4. Try uploading the Arduino code again")
    print("  5. Restart the Arduino and try again")

if __name__ == "__main__":
    result = asyncio.run(diagnose())
    if result:
        print(f"\nSave this address to use later:")
        print(f"  {result}")
