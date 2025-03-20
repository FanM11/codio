from django.db import models

class Airline(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class City(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "cities"

class Route(models.Model):
    source_city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='departures')
    destination_city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='arrivals')

    def __str__(self):
        return f"{self.source_city} → {self.destination_city}"

    class Meta:
        unique_together = ('source_city', 'destination_city')

class Flight(models.Model):
    airline = models.ForeignKey(Airline, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    departure_date = models.DateField()
    departure_time = models.TimeField()
    duration_minutes = models.IntegerField()
    total_stops = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    additional_info = models.TextField(blank=True)

    def __str__(self):
        return f"{self.airline} - {self.route} - {self.departure_date}"

class Booking(models.Model):
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE)
    user_id = models.IntegerField()
    passenger_name = models.CharField(max_length=100, null=True, blank=True)
    passenger_email = models.EmailField(null=True, blank=True)
    passenger_phone = models.CharField(max_length=20, null=True, blank=True)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=[
            ('pending', '待确认'),
            ('confirmed', '已确认'),
            ('cancelled', '已取消')
        ],
        default='pending'
    )

    def __str__(self):
        return f"{self.passenger_name or 'Unknown'} - {self.flight}"


# flights/models.py
# models.py 中的 TempBooking 类修改
class TempBooking(models.Model):
    BOOKING_STAGES = [
        ('searching', '搜索航班'),
        ('selecting', '选择航班'),
        ('collecting_info', '收集信息'),
        ('confirming', '确认预订'),
        ('modifying', '修改订单')  # 添加修改状态
    ]

    session_id = models.CharField(max_length=100, unique=True)
    source_city = models.ForeignKey(City, null=True, on_delete=models.SET_NULL, related_name='temp_departures')
    destination_city = models.ForeignKey(City, null=True, on_delete=models.SET_NULL, related_name='temp_arrivals')
    departure_date = models.DateField(null=True)
    passenger_name = models.CharField(max_length=100, null=True)
    passenger_phone = models.CharField(max_length=20, null=True)
    passenger_email = models.EmailField(null=True)
    preferred_time = models.CharField(max_length=20, null=True)
    available_flights = models.CharField(max_length=200, null=True)
    selected_flight_id = models.IntegerField(null=True)
    booking_stage = models.CharField(max_length=20, choices=BOOKING_STAGES, default='searching')
    created_at = models.DateTimeField(auto_now_add=True)
    modification_id = models.IntegerField(null=True)  # 添加修改订单ID字段
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled')
        ],
        default='pending'
    )

    class Meta:
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['status']),
            models.Index(fields=['booking_stage']),
            models.Index(fields=['modification_id'])  # 添加索引
        ]

    def __str__(self):
        return f"Session: {self.session_id} - Stage: {self.booking_stage}"

    def get_flight_info(self):
        """返回已选择航班的信息"""
        if not self.selected_flight_id:
            return None

        try:
            flight = Flight.objects.get(id=self.selected_flight_id)
            return {
                'id': flight.id,
                'airline': flight.airline.name,
                'source': flight.route.source_city.name,
                'destination': flight.route.destination_city.name,
                'date': flight.departure_date,
                'time': flight.departure_time,
                'price': flight.price,
                'duration': flight.duration_minutes
            }
        except Flight.DoesNotExist:
            return None

    def is_ready_for_confirmation(self):
        """检查是否已收集足够信息可以确认预订"""
        return (
                self.booking_stage == 'collecting_info' and
                self.selected_flight_id is not None and
                self.passenger_name is not None and
                self.passenger_email is not None and
                self.passenger_phone is not None
        )