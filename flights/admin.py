from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Airline, City, Route, Flight, Booking

admin.site.register(Airline)
admin.site.register(City)
admin.site.register(Route)
admin.site.register(Flight)
admin.site.register(Booking)