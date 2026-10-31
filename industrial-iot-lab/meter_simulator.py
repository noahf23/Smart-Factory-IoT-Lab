"""Simulate four meters, a source heartbeat, and controllable device faults."""

# I use only the standard library alongside the pinned Modbus dependency.
import argparse
import json
import time
from pathlib import Path
from pymodbus.constants import ExcCodes
from pymodbus.server import StartTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice
from lab_config import HOST, PORT, METERS


def make_action(device_id, fault_file):
    # I retain each device's last sample so a frozen source can still answer requests.
    started = time.monotonic()
    sample = list(METERS[device_id]["registers"]) + [0]

    async def action(function_code, start_address, address, count, current_registers, set_values):
        # I reject write requests; this simulator is intended for read-only monitoring.
        if function_code != 3:
            return ExcCodes.ILLEGAL_FUNCTION
        try:
            # I read a small control file so faults can change without restarting the server.
            modes = json.loads(fault_file.read_text(encoding="utf-8")) if fault_file.exists() else {}
            mode = modes.get(str(device_id), "normal")
        except (OSError, ValueError):
            # I report a device failure rather than silently accepting broken fault configuration.
            return ExcCodes.DEVICE_FAILURE
        if mode == "offline":
            # I simulate a gateway reporting an unavailable device, not a dropped TCP packet.
            return ExcCodes.GATEWAY_NO_RESPONSE
        if mode not in {"normal", "freeze"}:
            return ExcCodes.DEVICE_FAILURE
        if mode == "normal":
            # I advance a source heartbeat every 100 ms, independent of measurement changes.
            tick = int((time.monotonic() - started) * 10)
            # I vary current slightly so the display demonstrates changing simulated measurements.
            sample[:] = list(METERS[device_id]["registers"]) + [tick % 65536]
            sample[1] += tick % 5
        # I keep both measurements and heartbeat unchanged when the source is frozen.
        offset = 0 - start_address
        current_registers[offset:offset + 4] = sample
        return None

    return action


def main():
    # I expose optional test settings without changing the normal Windows launchers.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--fault-file", type=Path, default=Path(__file__).with_name("faults.json"))
    args = parser.parse_args()
    devices = []
    for device_id, meter in METERS.items():
        # I add register 3 as a fictional source heartbeat, not a standard meter feature.
        registers = SimData(address=0, values=meter["registers"] + [0], datatype=DataType.REGISTERS)
        devices.append(SimDevice(id=device_id, simdata=registers, action=make_action(device_id, args.fault_file)))
        print(f"Device {device_id}: {meter['name']}", flush=True)
    print(f"Starting simulated meters at {HOST}:{args.port}", flush=True)
    print(f"Fault controls: {args.fault_file}", flush=True)
    StartTcpServer(context=devices, address=(HOST, args.port))


# I start the server only when this file is executed directly.
if __name__ == "__main__":
    main()
