"""Scan Modbus meters with data quality, warning, recovery, and SQLite history."""

# I timestamp records in UTC and use a monotonic clock for elapsed-time decisions.
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import time
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from lab_config import HOST, PORT, METERS, HIGH_LIMITS, UNITS


def find_warnings(readings):
    # I compare actual returned measurements with configurable training limits.
    return [f"HIGH {key.upper()}: {value:.1f} {UNITS[key]} exceeds {HIGH_LIMITS[key]:.1f} {UNITS[key]}"
            for key, value in readings.items() if value > HIGH_LIMITS[key]]


class MeterState:
    """Track source freshness independently from successful TCP responses."""

    def __init__(self):
        # I start without a trusted sample and cannot assume a frozen source is fresh.
        self.heartbeat = None
        self.changed_at = None
        self.values = None
        self.last_good_utc = None
        self.status = None
        self.needs_confirmation = True
        self.recovery_pending = False

    def accept(self, registers, now, utc, stale_after):
        # I require the complete measurement and heartbeat block.
        if len(registers) != 4:
            raise ValueError("Expected four registers, including the source heartbeat.")
        self.values = dict(zip(("voltage", "current", "temperature"), [v / 10 for v in registers[:3]]))
        heartbeat = registers[3]
        if self.heartbeat is None:
            # I establish a baseline; a subsequent heartbeat change confirms freshness.
            self.changed_at = now
            quality = "WARMUP"
        elif heartbeat != self.heartbeat:
            self.changed_at = now
            self.last_good_utc = utc
            self.needs_confirmation = False
            quality = "FRESH"
        elif now - self.changed_at >= stale_after:
            quality = "STALE"
        else:
            quality = "FRESH" if self.last_good_utc and not self.needs_confirmation else "WARMUP"
        self.heartbeat = heartbeat
        return quality


def run_scan(client, states, stale_after, database):
    # I attempt every configured device, including after an earlier device fails.
    counts = {key: 0 for key in ("OK", "WARNING", "WARMUP", "STALE", "COMM_ERROR")}
    for device_id, meter in METERS.items():
        state = states[device_id]
        utc = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        values = None
        heartbeat = None
        warnings = []
        error = ""
        try:
            # I reconnect automatically on a later scan when the gateway returns.
            if not client.connected and not client.connect():
                raise ConnectionError("Gateway unavailable; start or restart the simulator.")
            response = client.read_holding_registers(0, count=4, device_id=device_id)
            if response.isError():
                raise ModbusException(str(response))
            quality = state.accept(response.registers, time.monotonic(), utc, stale_after)
            values, heartbeat = state.values, state.heartbeat
            warnings = find_warnings(values)
            # I never call stale or unconfirmed data OK, even when measurements are low.
            status = quality if quality != "FRESH" else ("WARNING" if warnings else "OK")
        except (ModbusException, OSError, ValueError) as exc:
            # I record missing measurements as NULL rather than reusing cached data as current.
            status, error = "COMM_ERROR", str(exc)
            state.needs_confirmation = True
        state.status = status
        if status in {"STALE", "COMM_ERROR"}:
            state.recovery_pending = True
        counts[status] += 1
        print(f"{utc} | Meter {device_id}: {meter['name']} | [{status}]", flush=True)
        if state.recovery_pending and status in {"OK", "WARNING"}:
            state.recovery_pending = False
            print("  [RECOVERED] Source heartbeat is advancing again.", flush=True)
        if values is not None:
            print("  " + " | ".join(f"{key}: {value:.1f} {UNITS[key]}" for key, value in values.items()), flush=True)
            for warning in warnings:
                print(f"  [WARNING] {warning}" + (" (untrusted freshness)" if status in {"STALE", "WARMUP"} else ""), flush=True)
        if status in {"STALE", "COMM_ERROR"}:
            print(f"  Last confirmed source update: {state.last_good_utc or 'not yet confirmed'}", flush=True)
        if error:
            print(f"  {error}", flush=True)
        # I persist each observation, including failed reads and source-quality status.
        database.execute("INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (utc, device_id, meter["name"], status,
             values["voltage"] if values else None, values["current"] if values else None,
             values["temperature"] if values else None, heartbeat, state.last_good_utc,
             error or "; ".join(warnings)))
    database.commit()
    print("Summary: " + ", ".join(f"{count} {status}" for status, count in counts.items()), flush=True)
    return counts


def positive(value):
    # I reject invalid timing settings before opening a network connection.
    number = float(value)
    if not 0 < number < float("inf"):
        raise argparse.ArgumentTypeError("Use a finite positive number.")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true", help="Poll until Ctrl+C")
    parser.add_argument("--cycles", type=int, help="Run a finite number of scans")
    parser.add_argument("--interval", type=positive, default=2.0)
    parser.add_argument("--stale-after", type=positive, default=10.0)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--database", type=Path, default=Path(__file__).parent / "data" / "monitoring.sqlite3")
    args = parser.parse_args()
    if args.cycles is not None and args.cycles < 1:
        parser.error("--cycles must be at least 1")
    if args.stale_after <= args.interval:
        parser.error("--stale-after must exceed --interval")
    args.database.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(args.database)
    database.execute("CREATE TABLE IF NOT EXISTS observations (observed_utc TEXT, device_id INTEGER, name TEXT, status TEXT, voltage REAL, current REAL, temperature REAL, heartbeat INTEGER, last_source_update_utc TEXT, detail TEXT)")
    client = ModbusTcpClient(HOST, port=args.port, timeout=1, retries=0)
    states = {key: MeterState() for key in METERS}
    scans = 0
    had_failure = False
    try:
        print(f"History: {args.database} | Source freshness requires a heartbeat change.", flush=True)
        while True:
            counts = run_scan(client, states, args.stale_after, database)
            had_failure |= bool(counts["STALE"] or counts["COMM_ERROR"])
            scans += 1
            if scans >= (args.cycles or (float("inf") if args.watch else 1)):
                break
            # I wait between completed scans; device timeouts can extend the actual cadence.
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Monitoring stopped by operator.")
    finally:
        client.close()
        database.close()
    # I distinguish successful monitoring with equipment warnings from data-quality failures.
    return 1 if had_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
