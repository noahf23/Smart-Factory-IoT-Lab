"""Set a simulated fault without changing the running monitor."""

# I write changes atomically so the simulator never reads a partially written file.
import argparse
import json
from pathlib import Path
from lab_config import METERS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device", choices=[str(key) for key in METERS] + ["all"])
    parser.add_argument("mode", choices=["normal", "freeze", "offline"])
    parser.add_argument("--fault-file", type=Path, default=Path(__file__).with_name("faults.json"))
    args = parser.parse_args()
    try:
        modes = json.loads(args.fault_file.read_text()) if args.fault_file.exists() else {}
        targets = list(METERS) if args.device == "all" else [int(args.device)]
        for device_id in targets:
            modes[str(device_id)] = args.mode
        temporary = args.fault_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(modes, indent=2), encoding="utf-8")
        temporary.replace(args.fault_file)
    except (OSError, ValueError, TypeError) as error:
        print(f"Fault configuration failed: {error}")
        return 1
    print(f"Simulation control: device {args.device} -> {args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
