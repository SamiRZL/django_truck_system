from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from services.trip_planner import generate_trip


@csrf_exempt
def plan_trip_view(request):

    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    origin = data.get("origin")
    pickup = data.get("pickup")
    destination = data.get("destination")
    current_cycle_used_hours = data.get("current_cycle_used_hours", 0)
    time= data.get("time")

    if not origin or not pickup or not destination:
        return JsonResponse(
            {"error": "origin, pickup, and destination are required"},
            status=400
        )

    try:
        result = generate_trip(
            origin=origin,
            pickup=pickup,
            destination=destination,
            time=time,
            current_cycle_used_hours=current_cycle_used_hours,
              )
        return JsonResponse(result, safe=False, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
