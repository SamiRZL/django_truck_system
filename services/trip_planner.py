from datetime import datetime, timedelta
from .google_client import call_routes_api, reverse_geocode
from utils.trip_utils import parse_duration, miles_from_meters, format_time, decode_poly
from rules.hos_rules import *

def generate_trip(origin, pickup, destination, time, current_cycle_used_hours=0):
    """Plan trip timeline based on Google Routes and HOS rules."""
    route_resp = call_routes_api(origin, destination, waypoints=[pickup])
    if not route_resp.get("routes"):
        return {"error": "No route returned from Routes API", "raw": route_resp}

    route = route_resp["routes"][0]
    total_miles = miles_from_meters(route["distanceMeters"])
    current_trip_time = datetime.fromisoformat(time)

    shift = 1
    timeline = []
    driving_state = None

    current_cycle_used_seconds = current_cycle_used_hours * 3600
    current_total_driving_time_in_shift = 0
    current_total_on_duty_time_in_shift = 0
    current_driving_time_from_brake = 0
    current_driving_distance_since_fuel = 0

    def record_interval(shift, type, reason, start_time, end_time, location=None):
        address = reverse_geocode(location["latitude"], location["longitude"]) if location else None
        duration = int((end_time - start_time).total_seconds() / 60)
        timeline.append({
            "shift": shift,
            "type": type,
            "reason": reason,
            "location": location,
            "address": address,
            "start_time": format_time(start_time),
            "end_time": format_time(end_time),
            "duration": duration,
        })

    def start_driving(start_time, location):
        return {"active": True, "start_time": start_time, "location": location}

    def end_driving(drive_state, end_time, shift, reason=""):
        if drive_state and drive_state.get("active"):
            record_interval(shift, DRIVING, reason, drive_state["start_time"], end_time, drive_state["location"])
            drive_state["active"] = False

    for leg_index, leg in enumerate(route["legs"]):
        for step_index, step in enumerate(leg["steps"]):
            step_duration = parse_duration(step.get("staticDuration", "0s"))
            step_distance_miles = miles_from_meters(step.get("distanceMeters", 0))
            is_last_step_of_leg = step_index == len(leg["steps"]) - 1

            start_lat = step["startLocation"]["latLng"]["latitude"]
            start_lng = step["startLocation"]["latLng"]["longitude"]
            end_lat = step["endLocation"]["latLng"]["latitude"]
            end_lng = step["endLocation"]["latLng"]["longitude"]

            remaining_step_duration = step_duration

            while remaining_step_duration > 0:
                if not driving_state or not driving_state.get("active"):
                    driving_state = start_driving(current_trip_time, {"latitude": start_lat, "longitude": start_lng})

                time_until_break = MAX_DRIVING_AFTER_BRAKE - current_driving_time_from_brake
                time_until_shift_end = MAX_DRIVING_TIME - current_total_driving_time_in_shift
                time_until_on_duty_end = MAX_HOURS_ON_DUTY - current_total_on_duty_time_in_shift
                time_until_cycle_end = MAX_CYCLE_SECONDS - current_cycle_used_seconds
                allowed_drive = min(
                    remaining_step_duration,
                    time_until_break,
                    time_until_shift_end,
                    time_until_on_duty_end,
                    time_until_cycle_end,
                )

                if allowed_drive <= 0:
                    end_driving(driving_state, current_trip_time, shift)
                    reset_end = current_trip_time + CYCLE_RESET_DURATION
                    record_interval(shift, SLEEPER_BERTH, "34 hour cycle reset", current_trip_time, reset_end)
                    current_trip_time = reset_end
                    current_total_driving_time_in_shift = 0
                    current_total_on_duty_time_in_shift = 0
                    current_driving_time_from_brake = 0
                    current_cycle_used_seconds = 0
                    shift += 1
                    break

                fraction_driven = allowed_drive / remaining_step_duration
                partial_lat = start_lat + fraction_driven * (end_lat - start_lat)
                partial_lng = start_lng + fraction_driven * (end_lng - start_lng)

                current_trip_time += timedelta(seconds=allowed_drive)
                current_total_driving_time_in_shift += allowed_drive
                current_total_on_duty_time_in_shift += allowed_drive
                current_driving_time_from_brake += allowed_drive
                current_cycle_used_seconds += allowed_drive
                current_driving_distance_since_fuel += step_distance_miles * fraction_driven

                remaining_step_duration -= allowed_drive

                if current_driving_time_from_brake >= MAX_DRIVING_AFTER_BRAKE:
                    end_driving(driving_state, current_trip_time, shift)
                    break_end = current_trip_time + BREAK_DURATION
                    record_interval(shift, OFF_DUTY, "30 min break", current_trip_time, break_end,
                                    {"latitude": partial_lat, "longitude": partial_lng})
                    current_trip_time = break_end
                    current_driving_time_from_brake = 0
                    current_total_on_duty_time_in_shift += BREAK_DURATION.total_seconds()

                elif current_total_driving_time_in_shift >= MAX_DRIVING_TIME or \
                     current_total_on_duty_time_in_shift >= MAX_HOURS_ON_DUTY:
                    end_driving(driving_state, current_trip_time, shift)
                    rest_end = current_trip_time + REST_DURATION
                    record_interval(shift, SLEEPER_BERTH, "10 hour rest", current_trip_time, rest_end,
                                    {"latitude": partial_lat, "longitude": partial_lng})
                    current_trip_time = rest_end
                    shift += 1
                    current_total_driving_time_in_shift = 0
                    current_total_on_duty_time_in_shift = 0
                    current_driving_time_from_brake = 0

                elif current_driving_distance_since_fuel >= FUEL_MILES_DISTANCE:
                    end_driving(driving_state, current_trip_time, shift)
                    fuel_end = current_trip_time + FUEL_DURATION
                    record_interval(shift, ON_DUTY, "Fueling", current_trip_time, fuel_end,
                                    {"latitude": partial_lat, "longitude": partial_lng})
                    current_trip_time = fuel_end
                    current_total_on_duty_time_in_shift += FUEL_DURATION.total_seconds()
                    current_cycle_used_seconds += FUEL_DURATION.total_seconds()
                    current_driving_distance_since_fuel = 0

            if is_last_step_of_leg:
                end_driving(driving_state, current_trip_time, shift)
                stop_type = "Pickup point" if leg_index == 0 else "Dropoff point"
                stop_end = current_trip_time + STOP_DURATION
                record_interval(shift, ON_DUTY, stop_type, current_trip_time, stop_end,
                                {"latitude": end_lat, "longitude": end_lng})
                current_trip_time = stop_end

    end_driving(driving_state, current_trip_time, shift)

    return {
        "polyline": decode_poly(route["polyline"]["encodedPolyline"]),
        "summary": {
            "total_miles": round(total_miles, 2),
            "predicted_driving_time": int(parse_duration(route["duration"]) / 3600),
            "total_shifts": shift,
            "total_estimated_arrival": format_time(current_trip_time),
        },
        "timeline": timeline,
    }
