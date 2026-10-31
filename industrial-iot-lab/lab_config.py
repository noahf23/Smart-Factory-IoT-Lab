"""Shared connection settings, simulated meters, and demonstration limits."""

# I keep every simulated device on the local computer at one gateway endpoint.
HOST = "127.0.0.1"
PORT = 1502

# I use independent device IDs to represent four meters behind one TCP gateway.
# I store voltage, current, and temperature as integers scaled by ten.
METERS = {
    1: {"name": "Main incomer", "registers": [4800, 125, 350]},
    2: {"name": "Production feeder", "registers": [4800, 320, 420]},
    3: {"name": "Test station", "registers": [4800, 180, 720]},
    4: {"name": "Auxiliary panel", "registers": [5100, 350, 750]},
}

# I define training thresholds, not equipment protection settings or ratings.
# I raise a warning only when a reading is strictly greater than its limit.
HIGH_LIMITS = {"voltage": 504.0, "current": 25.0, "temperature": 60.0}

# I keep units separate from values so warning messages are easy to interpret.
UNITS = {"voltage": "V", "current": "A", "temperature": "deg C"}
