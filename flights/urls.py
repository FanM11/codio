from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'airlines', views.AirlineViewSet)
router.register(r'cities', views.CityViewSet)
router.register(r'routes', views.RouteViewSet)
router.register(r'flights', views.FlightViewSet)
router.register(r'bookings', views.BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
    path('chat/', views.chat, name='chat'),
    path('booking-state/', views.get_booking_state, name='booking-state'),
]