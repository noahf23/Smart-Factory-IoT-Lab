# Industrial IoT Monitoring and Fault Detection Lab

## Overview

I developed this software-based portfolio lab with AI assistance to demonstrate industrial data acquisition, measurement scaling, equipment warnings, source-data quality, and troubleshooting. I use Python and Modbus TCP to monitor four simulated meters behind one local gateway endpoint. I store timestamped observations in SQLite and demonstrate both faults and recovery.

My focus is the communication and monitoring workflow relevant to connected-equipment testing. This project uses simulated inputs and a custom register map; it is not a Schneider Electric product emulator or a physical switchgear commissioning project.

## Windows quick start

Python 3.10 or newer must already be installed. Development verification used Python 3.14.7 and PyModbus 3.16.1.

1. I extract the entire ZIP before opening any launcher.
2. I run SETUP.bat once. It installs the bundled PyModbus wheel into a local .venv without internet access.
3. I run START_METER.bat and leave its window open.
4. I run MONITOR.bat for continuous monitoring, or READ_METER.bat for a two-scan check.
5. I use FAULT_DEMO.bat to freeze meter 3, make meter 2 unavailable, or restore all meters.
6. I stop monitoring and the simulator with Ctrl+C in their respective windows.

If I already have the previous lab running, I close its simulator and reader windows before launching this version. No administrator access, hardware, Docker, cloud account, or firewall changes are needed for the local lab.

## Architecture

```text
Four simulated meter register banks (device IDs 1-4)
          |                  ^
   Modbus TCP                | fault controls from faults.json
   127.0.0.1:1502            | via FAULT_DEMO.bat
          v
Sequential Python collector
          |
   Register scaling + source-heartbeat tracking
          |
   Equipment warnings + data-quality status + recovery events
          |
   UTC console output + SQLite observation history
```

I represent several meters behind one gateway using distinct logical device IDs. In a real installation, meters might instead have individual IP addresses. I bind the simulator to loopback and reject write requests; this monitor does not operate equipment.

## Devices and training scenarios

| ID | Name | Voltage | Base current | Temperature | Expected equipment warnings |
|---|---|---|---|---|---|
| 1 | Main incomer | 480.0 V | 12.5 A | 35.0 deg C | None |
| 2 | Production feeder | 480.0 V | 32.0 A | 42.0 deg C | High current |
| 3 | Test station | 480.0 V | 18.0 A | 72.0 deg C | High temperature |
| 4 | Auxiliary panel | 510.0 V | 35.0 A | 75.0 deg C | High voltage, current, temperature |

I vary current by 0.0-0.4 A to demonstrate changing simulated inputs. The configured high limits are 504.0 V, 25.0 A, and 60.0 deg C. A warning requires a reading strictly greater than its limit. These arbitrary training limits are not equipment ratings or protection settings.

## Register map

I use function code 03 to read four holding registers with zero-based protocol addresses. Each register is an unsigned 16-bit integer.

| Address | Meaning | Decoding |
|---|---|---|
| 0 | Voltage | raw / 10, volts |
| 1 | Current | raw / 10, amps |
| 2 | Temperature | raw / 10, degrees Celsius |
| 3 | Source heartbeat | unscaled counter, changes every 100 ms, wraps at 65536 |

Register 3 is my fictional source-quality mechanism. Real meters may expose a sequence number, acquisition timestamp, or diagnostic status instead, or may provide no equivalent. Unchanging electrical measurements alone do not prove stale data. Before adapting this lab, I would confirm the manufacturer's register map, units, scaling, word order, and freshness indicators.

## Data-quality and warning states

| Status | Meaning in my monitor |
|---|---|
| WARMUP | I have a response but have not confirmed a source-heartbeat change. |
| OK | I have confirmed freshness and readings are within the configured high limits. |
| WARNING | I have confirmed freshness and at least one reading is above its high limit. |
| STALE | Requests succeed but the source heartbeat has not advanced for at least 10 seconds. |
| COMM_ERROR | A connection, protocol, or response-validation failure prevented a valid read. |
| RECOVERED | A console event reports renewed freshness after a stale or failed device. |

I keep a separate state for each meter. A failed read does not make cached values current, and a stale meter is never labelled OK. I continue reading the other devices when one fails. Warnings displayed during WARMUP or STALE are explicitly marked as having untrusted freshness.

My default polling delay is two seconds after each completed scan. Requests are sequential with a one-second timeout and no request retries, so failures can extend the scan duration. Staleness is assessed on successful responses; communication failure is shown immediately as COMM_ERROR. Recovery after a failed read requires a heartbeat change before I report fresh data again.

The heartbeat is a demonstration freshness signal, not cryptographic evidence or a guaranteed physical acquisition timestamp. The 16-bit wrap can alias if a sampling interval exactly spans a full counter cycle. I do not use this lab for protective decisions.

## Interview demonstration: approximately three minutes

1. I start the simulator and MONITOR.bat. The first scan shows WARMUP; the next normally shows one OK meter and three meters with equipment warnings.
2. I open FAULT_DEMO.bat and choose 1 to freeze meter 3. After roughly 10 seconds plus scan timing, its state becomes STALE while the other meters continue updating.
3. I choose 2 to make meter 2 unavailable. The simulator returns Modbus gateway exception 11; the monitor reports COMM_ERROR for that device without interrupting healthy devices.
4. I choose 3 to restore all devices. The monitor confirms advancing heartbeats and reports RECOVERED; the original equipment warnings remain because restoring communication does not remove high readings.
5. I stop the simulator while leaving the monitor open. All meters become COMM_ERROR. I restart the simulator and observe automatic reconnection and recovery.
6. I stop the monitor and review the recorded verification and database history.

The offline scenario is a simulated gateway exception, not a physical link interruption. Stopping the server separately exercises loss of the TCP endpoint. Fault settings persist across restarts, so I restore all devices before starting a new demonstration.

## Persistent history

I write every device observation to data/monitoring.sqlite3 using Python's standard-library SQLite driver. I record UTC observation time, device ID, name, status, measurements, source heartbeat, last confirmed source-update observation, and error or warning details.

COMM_ERROR rows contain NULL measurements rather than cached values. STALE rows contain the returned values together with their explicit STALE status. UTC observation time is the start of a device read, and last_source_update_utc is when I observed a heartbeat change, not a timestamp generated by a real meter. SQLite data persists between monitoring sessions. I have not implemented retention or log rotation.

Example query in a SQLite browser:

```sql
SELECT observed_utc, device_id, status, voltage, current, temperature, detail
FROM observations
ORDER BY observed_utc DESC, device_id
LIMIT 20;
```

## Verification and evidence

I run VERIFY_LAB.bat to reproduce the tests against an isolated temporary server, fault-control file, and database. It does not change the normal lab fault settings or history. Deliberate connection errors during verification are expected; the final PASS message and exit code 0 indicate success. VALIDATION.txt contains the recorded development run.

Checks cover threshold boundaries, initial freshness, heartbeat wrap, malformed response length, four-device acquisition, individual faults, stale detection, recovery, gateway loss and restart, rejected writes, persisted observations, NULL failed measurements, healthy and failed CLI exit codes, and invalid timing arguments.

Normal high readings do not make the program fail. Exit code 1 means the session encountered at least one STALE or COMM_ERROR state, even if it later recovered. Exit code 0 means the session encountered neither. A one-scan read can remain WARMUP, so the Windows read launcher requests two scans. Argument errors return code 2.

## Configuration and troubleshooting

I edit lab_config.py to change meter names, device IDs, raw values, and demonstration high limits. I restart both server and reader after changing shared configuration. I use fault_control.py or FAULT_DEMO.bat for live fault changes.

| Problem | My initial checks |
|---|---|
| Missing pymodbus module | I run SETUP.bat and use the provided launchers, which select .venv. |
| Connection refused | I confirm the simulator is running and the port matches. |
| Address already in use | I close an older simulator using port 1502. |
| Unexpected stale state | I restore fault controls and check the source-heartbeat assumptions. |
| Wrong measurement | I compare raw values with the documented conversion and units. |
| Database access error | I check folder permissions, free space, and conflicting database locks. |

Advanced examples, from this project folder:

```powershell
# I run five scans using the local environment.
.\.venv\Scripts\python.exe read_meter.py --cycles 5

# I change polling and freshness thresholds for an isolated demonstration.
.\.venv\Scripts\python.exe read_meter.py --watch --interval 1 --stale-after 5

# I restore all simulated devices without the menu.
.\.venv\Scripts\python.exe fault_control.py all normal
```

## Scope and limitations

I demonstrate a software monitoring workflow with simulated devices. I have not validated physical switchgear, production networks, long-duration operation, sensor accuracy, authentication, encryption, IEC 62443 compliance, or protection functions. The monitor has no dashboard, notification delivery, hysteresis, alarm acknowledgement, or escalation workflow. Console warnings are recalculated each scan. The SQLite log has no retention policy, and this is not a managed Windows service.

A real pilot would require an approved device and register map, validated thresholds, reviewed network access, data-quality semantics appropriate to the equipment, resource/load testing, and commissioning evidence under site procedures.

## Project files

- lab_config.py: my connection settings, meters, limits, and units.
- meter_simulator.py: my dynamic simulator and controlled fault responses.
- read_meter.py: my polling, quality tracking, warnings, recovery, and history.
- fault_control.py / faults.json: my interactive fault configuration.
- verify_lab.py / VALIDATION.txt: reproducible verification and recorded output.
- Windows .bat files: setup, simulator, read, monitor, fault menu, and verification.
- PROJECT_SUMMARY.md: my application-ready project description and resume wording.
- packages / requirements.txt: the offline dependency and pinned version.

Reference: [Official PyModbus documentation](https://pymodbus.readthedocs.io/).
