from rest_framework import serializers
from .models import Airline, City, Route, Flight, Booking


class AirlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airline
        fields = ['id', 'name']


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name']


class RouteSerializer(serializers.ModelSerializer):
    source_city = CitySerializer(read_only=True)
    destination_city = CitySerializer(read_only=True)

    class Meta:
        model = Route
        fields = ['id', 'source_city', 'destination_city']


class FlightSerializer(serializers.ModelSerializer):
    airline = AirlineSerializer(read_only=True)
    route = RouteSerializer(read_only=True)

    class Meta:
        model = Flight
        fields = [
            'id', 'airline', 'route', 'departure_date',
            'departure_time', 'duration_minutes', 'total_stops',
            'price', 'additional_info'
        ]


class FlightSearchSerializer(serializers.Serializer):
    source = serializers.CharField(required=True)
    destination = serializers.CharField(required=True)
    date = serializers.DateField(required=True)


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'flight', 'user_id', 'passenger_name',
            'passenger_email', 'passenger_phone'
        ]


class BookingSerializer(serializers.ModelSerializer):
    flight = FlightSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'flight', 'user_id', 'passenger_name',
            'passenger_email', 'passenger_phone',
            'booking_date', 'status'
        ]