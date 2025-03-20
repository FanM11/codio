from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Airline, City, Route, Flight, Booking, TempBooking
from .serializers import (
    AirlineSerializer,
    CitySerializer,
    RouteSerializer,
    FlightSerializer,
    FlightSearchSerializer,
    BookingSerializer,
    BookingCreateSerializer
)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .utils import DialogManager
import logging
import json

logger = logging.getLogger('ChatSystem')


@api_view(['POST'])
def chat(request):
    try:
        message = request.data.get('message', '')
        session_id = request.data.get('session_id', '')

        if not message:
            return Response({
                'message': 'Please enter your message'
            })

        if not session_id:
            return Response({
                'message': 'Session error, please refresh the page'
            })

        # 移除删除操作，改为获取或创建
        try:
            temp_booking = TempBooking.objects.get(
                session_id=session_id,
                status='pending'
            )
        except TempBooking.DoesNotExist:
            temp_booking = TempBooking.objects.create(
                session_id=session_id,
                status='pending'
            )

        # Process message
        dialog_manager = DialogManager()
        dialog_manager.session_id = session_id
        response = dialog_manager.process_message(message)

        # Check if a booking was created
        try:
            updated_booking = TempBooking.objects.get(session_id=session_id)
            if updated_booking.status == 'confirmed':
                # Get the related booking
                bookings = Booking.objects.filter(
                    passenger_email=updated_booking.passenger_email,
                    passenger_phone=updated_booking.passenger_phone
                ).order_by('-booking_date')[:1]

                if bookings.exists():
                    booking = bookings[0]
                    booking_info = {
                        'id': booking.id,
                        'flight_id': booking.flight.id,
                        'airline': booking.flight.airline.name,
                        'passenger_name': booking.passenger_name,
                        'status': booking.status
                    }

                    # Include booking info in response
                    return Response({
                        'message': response,
                        'booking_created': True,
                        'booking_info': booking_info
                    })
        except Exception as e:
            logger.error(f"Error checking booking status: {e}")

        return Response({
            'message': response
        })

    except Exception as e:
        logger.error(f"Error in chat view: {str(e)}")
        return Response({
            'message': 'System error, please try again later'
        })


@api_view(['GET'])
def get_booking_state(request):
    """获取当前会话的预订状态"""
    try:
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': 'Missing session_id parameter'}, status=400)

        try:
            booking = TempBooking.objects.get(session_id=session_id)

            response_data = {
                'booking_stage': booking.booking_stage,
                'status': booking.status
            }

            # 基于阶段添加所需信息
            if booking.source_city:
                response_data['source_city'] = booking.source_city.name
            if booking.destination_city:
                response_data['destination_city'] = booking.destination_city.name
            if booking.departure_date:
                response_data['departure_date'] = booking.departure_date.isoformat()

            # 如果已选择航班，则包含航班信息
            if booking.selected_flight_id:
                flight_info = booking.get_flight_info()
                if flight_info:
                    response_data['flight_info'] = flight_info

            # 如果到了收集信息阶段，则包含乘客信息
            if booking.booking_stage in ['collecting_info', 'confirming']:
                passenger_info = {
                    'name': booking.passenger_name,
                    'email': booking.passenger_email,
                    'phone': booking.passenger_phone
                }
                response_data['passenger_info'] = passenger_info

            return Response(response_data)

        except TempBooking.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

    except Exception as e:
        logger.error(f"Error in get_booking_state: {str(e)}")
        return Response({'error': 'Internal server error'}, status=500)


class AirlineViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Airline.objects.all()
    serializer_class = AirlineSerializer


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer


class FlightViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Flight.objects.select_related('airline', 'route', 'route__source_city', 'route__destination_city')
    serializer_class = FlightSerializer

    @action(detail=False, methods=['post'])
    def search(self, request):
        print("Received search request:", request.data)
        serializer = FlightSearchSerializer(data=request.data)
        if serializer.is_valid():
            source = serializer.validated_data['source']
            destination = serializer.validated_data['destination']
            date = serializer.validated_data['date']

            flights = self.get_queryset().filter(
                route__source_city__name__iexact=source,
                route__destination_city__name__iexact=destination,
                departure_date=date
            )

            print(f"Found {flights.count()} flights")
            return Response(
                FlightSerializer(flights, many=True).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookingViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = Booking.objects.all()

        # 添加过滤参数
        booking_id = self.request.query_params.get('id')
        passenger_name = self.request.query_params.get('name')
        passenger_email = self.request.query_params.get('email')
        passenger_phone = self.request.query_params.get('phone')

        # 根据参数进行过滤
        if booking_id:
            queryset = queryset.filter(id=booking_id)
        if passenger_name:
            queryset = queryset.filter(passenger_name__icontains=passenger_name)
        if passenger_email:
            queryset = queryset.filter(passenger_email__iexact=passenger_email)
        if passenger_phone:
            queryset = queryset.filter(passenger_phone__iexact=passenger_phone)

        logger.info(f"Fetching bookings with filters, count: {queryset.count()}")
        return queryset.select_related(
            'flight',
            'flight__airline',
            'flight__route',
            'flight__route__source_city',
            'flight__route__destination_city'
        )

    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'update' or self.action == 'partial_update':
            return BookingCreateSerializer
        return BookingSerializer

    def create(self, request, *args, **kwargs):
        logger.info("Creating booking with data:", request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = self.perform_create(serializer)
        logger.info("Created booking:", booking)
        headers = self.get_success_headers(serializer.data)
        return Response(
            BookingSerializer(booking).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def perform_create(self, serializer):
        return serializer.save()

    def update(self, request, *args, **kwargs):
        """更新预订信息"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # 记录原始状态
        original_flight_id = instance.flight.id if instance.flight else None

        # 更新数据
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()

        # 记录更新后的状态
        new_flight_id = updated_instance.flight.id if updated_instance.flight else None

        # 记录更改
        if original_flight_id != new_flight_id:
            logger.info(f"Booking {instance.id} flight changed from {original_flight_id} to {new_flight_id}")

        logger.info(f"Booking {instance.id} updated successfully")

        return Response(BookingSerializer(updated_instance).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消预订"""
        booking = self.get_object()
        booking.status = 'cancelled'
        booking.save()
        logger.info(f"Booking {booking.id} cancelled")
        return Response(
            BookingSerializer(booking).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def find(self, request):
        """通过各种条件查找预订"""
        booking_id = request.query_params.get('id')
        passenger_name = request.query_params.get('name')
        passenger_email = request.query_params.get('email')
        passenger_phone = request.query_params.get('phone')

        if not any([booking_id, passenger_name, passenger_email, passenger_phone]):
            return Response(
                {"error": "At least one search parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.get_queryset()

        if not queryset.exists():
            return Response(
                {"message": "No bookings found with the provided criteria"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(BookingSerializer(queryset, many=True).data)

    # @action(detail=False, methods=['post'])
    # def create_from_temp(self, request, *args, **kwargs):
    #     """从临时预订创建正式预订"""
    #     try:
    #         session_id = request.data.get('session_id')
    #         if not session_id:
    #             return Response({'error': 'Missing session_id'}, status=400)
    #
    #         try:
    #             temp_booking = TempBooking.objects.get(session_id=session_id)
    #         except TempBooking.DoesNotExist:
    #             return Response({'error': 'Temp booking not found'}, status=404)
    #
    #         # 验证临时预订是否包含所有必要信息
    #         if not temp_booking.selected_flight_id or not temp_booking.passenger_name or \
    #                 not temp_booking.passenger_email or not temp_booking.passenger_phone:
    #             return Response({'error': 'Incomplete booking information'}, status=400)
    #
    #         # 获取选定的航班
    #         try:
    #             flight = Flight.objects.get(id=temp_booking.selected_flight_id)
    #         except Flight.DoesNotExist:
    #             return Response({'error': 'Selected flight not found'}, status=404)
    #
    #         # 创建正式预订
    #         booking = Booking.objects.create(
    #             flight=flight,
    #             user_id=request.data.get('user_id', 1),  # 使用请求中的用户ID或默认值
    #             passenger_name=temp_booking.passenger_name,
    #             passenger_email=temp_booking.passenger_email,
    #             passenger_phone=temp_booking.passenger_phone,
    #             status='confirmed'
    #         )
    #
    #         # 更新临时预订状态
    #         temp_booking.status = 'confirmed'
    #         temp_booking.save()
    #
    #         return Response(
    #             BookingSerializer(booking).data,
    #             status=status.HTTP_201_CREATED
    #         )
    #
    #     except Exception as e:
    #         logger.error(f"Error in create_from_temp: {str(e)}")
    #         return Response({'error': 'Internal server error'}, status=500)