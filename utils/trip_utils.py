from datetime import datetime
import polyline

METER_PER_MILE = 1609.344
FUEL_METER_THRESHOLD = 1000 * METER_PER_MILE

def parse_duration(duration_value):
    """Convert duration string (e.g., '45s') or numeric into seconds (float)."""
    if isinstance(duration_value, str):
        return float(duration_value.replace('s', ''))
    return float(duration_value)

def miles_from_meters(meters):
    return meters * 0.000621371

def format_time(dt):
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def decode_poly(encoded_poly):
    return polyline.decode(encoded_poly)
