from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.contrib.gis.geos import Point
from decimal import Decimal

from .models import Ride
from .serializers import RideSerializer
from src.apps.accounts.models import DriverProfile
from src.apps.accounts.permissions import IsRider
from .utils import calculate_dynamic_fare

class CreateRideView(APIView):
    permission_classes = [IsRider]

    def calculate_aruba_fare(self, pickup_point, dropoff_point):
        """
        Aruba Pricing Logic
        Note: distance is in degrees by default in PostGIS if not transformed, 
        but .distance() on points gives a rough estimate. 
        For accuracy in KM, we use GEOS distance.
        """
        # Calculate rough distance in KM (1 degree is approx 111km)
        distance_in_km = pickup_point.distance(dropoff_point) * 111
        
        base_fare = Decimal('5.00')
        per_km_rate = Decimal('2.50')
        
        subtotal = base_fare + (Decimal(str(distance_in_km)) * per_km_rate)
        
        # Aruba Taxes (BBO/BAVP/BAZV approx 7%)
        tax_rate = Decimal('0.07')
        total_fare = subtotal * (1 + tax_rate)
        
        return round(total_fare, 2)

    def post(self, request):
        serializer = RideSerializer(data=request.data)
        if serializer.is_valid():
            # 1. Extract Details
            v_type = request.data.get('requested_vehicle_type', 'ECONOMY')
            p_lat, p_lng = serializer.validated_data['pickup_lat'], serializer.validated_data['pickup_lng']
            d_lat, d_lng = serializer.validated_data['dropoff_lat'], serializer.validated_data['dropoff_lng']
            
            pickup_p = Point(p_lng, p_lat, srid=4326)
            dropoff_p = Point(d_lng, d_lat, srid=4326)

            # 2. Dynamic Fare Calculation
            estimated_price = calculate_dynamic_fare(pickup_p, dropoff_p, v_type)

            # 3. Save Ride
            ride = serializer.save(
                rider=request.user,
                requested_vehicle_type=v_type,
                estimated_price=estimated_price,
                status='SEARCHING'
            )
            
            # 4. Find Nearby Drivers
            nearby_drivers = DriverProfile.objects.filter(
                is_active=True,
                is_online=True,
                last_location__distance_lte=(ride.pickup_location, D(km=5))
            ).annotate(
                distance=Distance('last_location', ride.pickup_location)
            ).order_by('distance')

            # 5. Response
            response_data = RideSerializer(ride).data
            response_data['nearby_drivers_count'] = nearby_drivers.count()
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        



class RideHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_driver:
            # If driver, show rides they drove
            rides = Ride.objects.filter(driver=request.user).order_by('-created_at')
        else:
            # If rider, show rides they took
            rides = Ride.objects.filter(rider=request.user).order_by('-created_at')
        
        serializer = RideSerializer(rides, many=True)
        return Response(serializer.data)