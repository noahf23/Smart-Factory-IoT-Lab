# Industrial IoT Monitoring and Fault Detection Lab

## Portfolio summary

I developed a Windows-based industrial IoT monitoring lab with AI assistance using Python, Modbus TCP, and SQLite. I simulated four logical power meters behind one gateway and implemented sequential acquisition, register scaling, configurable warnings, UTC observations, and persistent history.

I distinguished high equipment readings from communication failure and stale source data. I used a simulated heartbeat to confirm freshness, retained per-device state, and verified that unavailable measurements were stored as NULL rather than presented as current readings. I added interactive fault injection and tested recovery after individual device failures and a full gateway restart.

The project demonstrates software communication and monitoring with simulated devices. It does not represent physical switchgear commissioning or a production deployment.

## Technical evidence

- Four independently addressed Modbus devices with documented register mapping.
- Continuous polling and configurable voltage, current, and temperature warnings.
- Initial freshness confirmation, stale-data detection, and recovery reporting.
- SQLite observation history with explicit data-quality states.
- Controlled frozen-source and unavailable-device scenarios.
- Reproducible verification, offline dependency packaging, and Windows launchers.

## Resume project entry

**Industrial IoT Monitoring and Fault Detection Lab | Python, Modbus TCP, SQLite, Windows**

- Developed a four-device simulated Modbus TCP monitoring lab with register decoding, configurable equipment warnings, UTC timestamps, and SQLite history.
- Implemented per-device freshness tracking, stale-data detection, communication-failure handling, and recovery reporting using a simulated source heartbeat.
- Validated device faults, gateway restart recovery, threshold boundaries, and failed-read data handling through reproducible automated checks; documented architecture and commissioning-style test scenarios.

## Application email paragraph

I have also included an industrial IoT monitoring lab that I developed with AI assistance to demonstrate my approach to connected-equipment monitoring and troubleshooting. The project uses Python, Modbus TCP, and SQLite to monitor four simulated meters, detect high readings and stale data, and record communication failures and recovery. The package includes source code, documented register mappings, Windows launchers, and reproducible verification.

## Concepts I should be ready to explain

- Why a device ID differs from an IP address, TCP port, and register address.
- How I convert raw register values into engineering units.
- Why successful communication does not guarantee fresh source data.
- Why stable measurement values alone cannot establish a frozen sensor.
- Why recovery from a network fault does not mean a high temperature has cleared.
- How I prevent missing readings from appearing as normal data.
- Which assumptions must change before connecting to a real manufacturer's meter.
