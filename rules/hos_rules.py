from datetime import timedelta

# Constants
MAX_CYCLE_SECONDS = 70 * 3600
MAX_HOURS_ON_DUTY = 14 * 3600
MAX_DRIVING_TIME = 11 * 3600
MAX_DRIVING_AFTER_BRAKE = 8 * 3600
FUEL_MILES_DISTANCE = 1000

# Status labels
ON_DUTY = "On Duty"
OFF_DUTY = "Off Duty"
DRIVING = "Driving"
SLEEPER_BERTH = "Sleeper Berth"

# Reset durations
BREAK_DURATION = timedelta(minutes=30)
REST_DURATION = timedelta(hours=10)
CYCLE_RESET_DURATION = timedelta(hours=34)
FUEL_DURATION = timedelta(minutes=30)
STOP_DURATION = timedelta(hours=1)
