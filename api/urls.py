from django.urls import path
from .views import plan_trip_view

urlpatterns = [
    path('route/', plan_trip_view, name='plan_trip_view'),
]
