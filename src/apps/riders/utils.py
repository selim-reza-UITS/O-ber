from decimal import Decimal

from src.apps.dashboard.models import PriceConfig

def calculate_dynamic_fare(pickup_point, dropoff_point, vehicle_type):
    """
    The Official Aruba Calculation Formula
    """
    try:
        # 1. Fetch the config from DB
        config = PriceConfig.objects.get(vehicle_type=vehicle_type)
    except PriceConfig.DoesNotExist:
        # Fallback to a default if the Admin hasn't set it up yet
        return Decimal('15.00')

    # 2. Calculate Distance (PostGIS distance is in degrees, roughly * 111 for KM)
    distance_km = Decimal(str(pickup_point.distance(dropoff_point) * 111.32))
    
    # 3. Estimate Duration (Distance / Average Speed of 40km/h * 60 minutes)
    # This fulfills the 'price_per_minute' requirement
    estimated_minutes = (distance_km / Decimal('40')) * Decimal('60')

    # 4. Apply Formula: Base + (Dist * Rate) + (Time * Rate)
    fare_subtotal = (
        config.base_fare + 
        (distance_km * config.price_per_km) + 
        (estimated_minutes * config.price_per_minute)
    )

    # 5. Add Aruba Tax (BBO/BAVP/BAZV)
    tax_multiplier = 1 + (config.aruba_tax_percentage / Decimal('100'))
    final_fare = fare_subtotal * tax_multiplier

    return round(final_fare, 2)