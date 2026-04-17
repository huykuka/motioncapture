"""
Standalone BLE / asyncio diagnostic script.
Run with:  python test_ble.py
It will scan, print every found device, then try to connect to Nano33BLE.
"""

import sys
import asyncio
import logging

# Enable bleak debug output so we can see exactly where the connection stalls
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
# Only show bleak logs (suppress other noisy loggers)
for name in logging.root.manager.loggerDict:
    if not name.startswith("bleak"):
        logging.getLogger(name).setLevel(logging.WARNING)

# ── Windows: fix COM apartment BEFORE importing anything BT-related ───────────
# Some libraries (pythoncom, win32com, …) silently initialise COM as STA.
# WinRT/bleak needs MTA; calling uninitialize_sta() undoes any premature STA init.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        from bleak.backends.winrt.util import uninitialize_sta
        uninitialize_sta()
    except Exception:
        pass

from bleak import BleakScanner, BleakClient

DEVICE_NAME = "Nano33BLE"
IMU_UUID    = "19B10001-E8F2-537E-4F6C-D104768A1214"
CMD_UUID    = "19B10002-E8F2-537E-4F6C-D104768A1214"
SCAN_SEC    = 10.0
CONN_SEC    = 20.0


async def scan() -> list:
    print(f"\n[SCAN] Scanning {SCAN_SEC}s …")
    found = await BleakScanner.discover(timeout=SCAN_SEC, return_adv=False)
    if not found:
        print("[SCAN] No devices found at all — is Bluetooth on?")
        return []
    for d in found:
        marker = " ← TARGET" if d.name == DEVICE_NAME else ""
        print(f"  {d.address}  name={d.name!r}{marker}")
    return found


async def connect(device) -> None:
    print(f"\n[CONNECT] Trying {device.name} @ {device.address} …")
    # use_cached_services=False forces Windows to re-enumerate GATT services
    # from the device directly, avoiding the ACTIVE->CLOSED drop caused by
    # a stale/empty Windows BLE service cache.
    kwargs = {"timeout": CONN_SEC}
    if sys.platform == "win32":
        kwargs["use_cached_services"] = False
    try:
        async with BleakClient(device, **kwargs) as client:
            print(f"[CONNECT] is_connected={client.is_connected}")
            if not client.is_connected:
                print("[CONNECT] ✗ connect() returned but is_connected is False.")
                print("          → The device connected briefly (GattSessionStatus.ACTIVE)")
                print("            and then immediately disconnected (CLOSED).")
                print("          → This is a FIRMWARE issue on the Arduino, not Python.")
                print("            Check your Arduino sketch for immediate disconnect/error.")
                return

            services = client.services
            print(f"[CONNECT] ✓ Connected! {len(services.services)} GATT service(s):")
            for svc in services:
                print(f"  service {svc.uuid}")
                for ch in svc.characteristics:
                    print(f"    char  {ch.uuid}  props={ch.properties}")

            char_uuids = [ch.uuid.lower() for svc in services for ch in svc.characteristics]
            if IMU_UUID.lower() in char_uuids:
                print(f"\n[OK] IMU characteristic found — testing start_notify …")
            else:
                print(f"\n[WARN] IMU characteristic {IMU_UUID} NOT found in GATT table.")
                return

            # Find handle directly (avoids UUID lookup issues)
            imu_handle = next(
                ch.handle for svc in services for ch in svc.characteristics
                if ch.uuid.lower() == IMU_UUID.lower()
            )
            cmd_handle = next(
                (ch.handle for svc in services for ch in svc.characteristics
                 if ch.uuid.lower() == CMD_UUID.lower()), None
            )

            def notify_handler(sender, data):
                print(f"  [NOTIFY] {len(data)} bytes: {data.hex()}")

            try:
                await client.start_notify(imu_handle, notify_handler)
                print("[OK] start_notify succeeded — waiting 3 s for data …")
                await asyncio.sleep(3)
            except Exception as e:
                print(f"[FAIL] start_notify: {type(e).__name__}: {e}")
                return

            if cmd_handle:
                try:
                    await client.write_gatt_char(cmd_handle, b"START")
                    print("[OK] write_gatt_char (START) succeeded")
                    await asyncio.sleep(2)
                    await client.write_gatt_char(cmd_handle, b"STOP")
                    print("[OK] write_gatt_char (STOP) succeeded")
                except Exception as e:
                    print(f"[FAIL] write_gatt_char: {type(e).__name__}: {e}")

    except asyncio.TimeoutError:
        print("[CONNECT] ✗ Timed out waiting for GattSessionStatus.ACTIVE.")
        print("          → The device was found but never accepted the connection.")
        print("          → Check: is the Arduino sketch running? Does it call BLE.begin()?")
        raise


async def main() -> None:
    print(f"Python  {sys.version}")
    import importlib.metadata
    print(f"bleak   {importlib.metadata.version('bleak')}")
    print(f"Policy  {type(asyncio.get_event_loop_policy()).__name__}")
    print(f"Loop    {type(asyncio.get_event_loop()).__name__}")

    # ── COM apartment type diagnostic ────────────────────────────────────────
    if sys.platform == "win32":
        try:
            from bleak.backends.winrt.util import assert_mta
            await assert_mta()
            print("COM     apartment OK (MTA or STA+message-loop)")
        except Exception as e:
            print(f"COM     WARNING: {e}")
            print("        → Try calling uninitialize_sta() before importing bleak.")

    devices = await scan()

    target = next((d for d in devices if d.name == DEVICE_NAME), None)
    if target is None:
        print(f"\n[WARN] '{DEVICE_NAME}' not seen — make sure it is powered on and advertising.")
        print("       Scan results above show everything that was found.")
        return

    # Retry up to 3 times – the device sometimes needs a moment after being found
    for attempt in range(1, 4):
        print(f"\n--- Connection attempt {attempt}/3 ---")
        try:
            await connect(target)
            break
        except Exception as exc:
            print(f"[ERROR] {type(exc).__name__}: {exc}")
            if attempt < 3:
                print("        Waiting 3 s before retry …")
                await asyncio.sleep(3)
            else:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
