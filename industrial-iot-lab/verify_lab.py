"""Reproduce boundary, source-quality, fault, recovery, and persistence checks."""

# I isolate verification from the normal lab endpoint, fault controls, and history.
import contextlib
import io
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pymodbus.client import ModbusTcpClient
from lab_config import HIGH_LIMITS
from read_meter import MeterState, find_warnings, run_scan


def main():
    # I exercise time boundaries deterministically without sleeping for unit checks.
    assert find_warnings(dict(HIGH_LIMITS)) == []
    assert len(find_warnings({key: value + 0.1 for key, value in HIGH_LIMITS.items()})) == 3
    state = MeterState()
    assert state.accept([4800, 125, 350, 65535], 0, "t0", 10) == "WARMUP"
    assert state.accept([4800, 125, 350, 65535], 10, "t1", 10) == "STALE"
    assert state.accept([4800, 125, 350, 0], 11, "t2", 10) == "FRESH"
    assert state.last_good_utc == "t2"
    # I require a new heartbeat after a communication failure, even inside the grace period.
    state.needs_confirmation = True
    assert state.accept([4800, 125, 350, 0], 11.1, "t2a", 10) == "WARMUP"
    assert state.accept([4800, 125, 350, 1], 11.2, "t2b", 10) == "FRESH"
    try:
        state.accept([1, 2, 3], 12, "t3", 10)
        raise AssertionError("Short response was accepted")
    except ValueError:
        pass
    folder = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as temporary:
        fault_file = Path(temporary) / "faults.json"
        fault_file.write_text("{}")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        server = subprocess.Popen([sys.executable, str(folder / "meter_simulator.py"), "--port", str(port), "--fault-file", str(fault_file)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        client = ModbusTcpClient("127.0.0.1", port=port, timeout=0.5, retries=0)
        database = sqlite3.connect(Path(temporary) / "history.sqlite3")
        database.execute("CREATE TABLE observations (observed_utc TEXT, device_id INTEGER, name TEXT, status TEXT, voltage REAL, current REAL, temperature REAL, heartbeat INTEGER, last_source_update_utc TEXT, detail TEXT)")
        states = {key: MeterState() for key in range(1, 5)}
        output = io.StringIO()
        try:
            for attempt in range(60):
                if server.poll() is not None:
                    raise RuntimeError(server.stderr.read())
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.1)
            with contextlib.redirect_stdout(output):
                counts = run_scan(client, states, 0.3, database)
                assert counts["WARMUP"] == 4
                time.sleep(0.15)
                counts = run_scan(client, states, 0.3, database)
                assert counts["OK"] == 1 and counts["WARNING"] == 3
                # I inject both fault types while the server continues running.
                for device, mode in (("2", "offline"), ("3", "freeze")):
                    controlled = subprocess.run([sys.executable, str(folder / "fault_control.py"), device, mode, "--fault-file", str(fault_file)], capture_output=True, text=True)
                    assert controlled.returncode == 0, controlled.stderr
                time.sleep(0.35)
                counts = run_scan(client, states, 0.3, database)
                assert counts["COMM_ERROR"] == 1 and counts["STALE"] == 1
                assert counts["OK"] == 1 and counts["WARNING"] == 1
                restored = subprocess.run([sys.executable, str(folder / "fault_control.py"), "all", "normal", "--fault-file", str(fault_file)], capture_output=True, text=True)
                assert restored.returncode == 0
                time.sleep(0.15)
                counts = run_scan(client, states, 0.3, database)
                assert counts["OK"] == 1 and counts["WARNING"] == 3
                assert output.getvalue().count("[RECOVERED]") == 2
                # I stop the entire gateway and verify cached values are not stored as current.
                server.terminate()
                server.wait(timeout=5)
                counts = run_scan(client, states, 0.3, database)
                assert counts["COMM_ERROR"] == 4
            assert database.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 20
            assert database.execute("SELECT COUNT(*) FROM observations WHERE status='COMM_ERROR' AND voltage IS NULL").fetchone()[0] == 5
            assert database.execute("SELECT COUNT(*) FROM observations WHERE status='STALE'").fetchone()[0] == 1
            # I check the public CLI exit status and argument validation as well.
            result = subprocess.run([sys.executable, str(folder / "read_meter.py"), "--port", str(port), "--database", str(Path(temporary) / "cli.sqlite3")], capture_output=True, text=True, timeout=15)
            assert result.returncode == 1
            invalid = subprocess.run([sys.executable, str(folder / "read_meter.py"), "--interval", "0"], capture_output=True, text=True)
            assert invalid.returncode == 2
            # I restart the whole gateway and confirm the same client reconnects.
            server.stderr.close()
            server = subprocess.Popen([sys.executable, str(folder / "meter_simulator.py"), "--port", str(port), "--fault-file", str(fault_file)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            for attempt in range(60):
                if server.poll() is not None:
                    raise RuntimeError(server.stderr.read())
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    time.sleep(0.1)
            with contextlib.redirect_stdout(output):
                run_scan(client, states, 0.3, database)
                time.sleep(0.15)
                counts = run_scan(client, states, 0.3, database)
                assert counts["OK"] == 1 and counts["WARNING"] == 3
            # I confirm the server rejects register writes.
            rejected = client.write_register(0, 1, device_id=1)
            assert rejected.isError()
            good = subprocess.run([sys.executable, str(folder / "read_meter.py"), "--port", str(port), "--cycles", "2", "--interval", "0.15", "--stale-after", "0.3", "--database", str(Path(temporary) / "healthy.sqlite3")], capture_output=True, text=True, timeout=15)
            assert good.returncode == 0, good.stdout + good.stderr
            assert "1 OK, 3 WARNING" in good.stdout
        finally:
            client.close()
            database.close()
            if server.poll() is None:
                server.terminate()
                server.wait(timeout=5)
            server.stderr.close()
    print(output.getvalue())
    print("PASS: threshold boundaries; initial freshness; heartbeat wrap; malformed response; four devices; per-device faults; stale detection; recovery; gateway failure; 20 persisted observations; NULL failed measurements; interactive fault-control CLI; gateway restart and reconnection; rejected writes; CLI healthy/failure exits and argument validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
