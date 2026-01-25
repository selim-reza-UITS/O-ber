from django.db.models import Sum, Count, F
from django.db.models.functions import TruncMonth, TruncYear
from src.apps.payments.models import Transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from .models import TermsAndConditionsModel, PrivacyAndPolicyModel, AboutUs, HelpSupport, PriceConfig, Notification
from .serializers import (
    TermsSerializer, PrivacySerializer, AboutUsSerializer, HelpSupportSerializer, 
    PriceConfigSerializer, NotificationSerializer, AdminUserListSerializer, 
    AdminTransactionSerializer, AdminRideListSerializer
)
from src.apps.accounts.models import DriverProfile, User, PendingDriverUpdate
from src.apps.accounts.serializers_driver import DriverProfileSerializer
from src.apps.accounts.services import SupportService
from src.apps.riders.models import Ride

class StaticContentBaseView(APIView):
    """Base View to handle Singleton-like behavior for static content"""
    model = None
    serializer_class = None

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_object(self):
        obj, created = self.model.objects.get_or_create(id=1)
        return obj

    def get(self, request):
        obj = self.get_object()
        serializer = self.serializer_class(obj)
        return Response(serializer.data)

    def patch(self, request):
        obj = self.get_object()
        serializer = self.serializer_class(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TermsView(StaticContentBaseView):
    model = TermsAndConditionsModel
    serializer_class = TermsSerializer

class PrivacyView(StaticContentBaseView):
    model = PrivacyAndPolicyModel
    serializer_class = PrivacySerializer

class AboutUsView(StaticContentBaseView):
    model = AboutUs
    serializer_class = AboutUsSerializer

class HelpSupportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = HelpSupportSerializer(data=request.data)
        if serializer.is_valid():
            support_instance = serializer.save(user=request.user)
            try:
                SupportService.send_support_email(
                    user_email=request.user.email,
                    message=support_instance.message
                )
            except Exception as e:
                print(f"Error sending support email: {e}")

            return Response({
                "message": "Support request sent successfully. Admin will review it.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- NEW ADMIN VIEWS ---

class AdminDashboardStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        year = request.query_params.get('year')
        
        # 1. Totals
        total_revenue = Transaction.objects.filter(status='SUCCESS').aggregate(Sum('amount'))['amount__sum'] or 0
        total_users = User.objects.filter(is_rider=True).count()
        total_drivers = DriverProfile.objects.filter(admin_verified=True).count()
        new_driver_requests = DriverProfile.objects.filter(admin_verified=False).count()

        # 2. Growth (User) - Group by Month
        user_growth_qs = User.objects.all()
        if year:
            user_growth_qs = user_growth_qs.filter(date_joined__year=year)
            
        user_growth = user_growth_qs.annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(count=Count('user_id')).order_by('month')

        # 3. Growth (Revenue) - Group by Month
        revenue_growth_qs = Transaction.objects.filter(status='SUCCESS')
        if year:
            revenue_growth_qs = revenue_growth_qs.filter(created_at__year=year)

        revenue_growth = revenue_growth_qs.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(total=Sum('amount')).order_by('month')
        
        return Response({
            "totals": {
                "revenue": total_revenue,
                "users": total_users,
                "drivers": total_drivers,
                "new_driver_requests": new_driver_requests
            },
            "growth": {
                "users": user_growth,
                "revenue": revenue_growth
            }
        })

class AdminUserListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.filter(is_rider=True)
    serializer_class = AdminUserListSerializer

    def delete(self, request, pk):
        try:
            user = User.objects.get(pk=pk, is_driver=False) # Prevent deleting drivers via rider endpoint accidentally?
            user.delete()
            return Response({"message": "User deleted"})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

class AdminDriverListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = DriverProfile.objects.all()
    serializer_class = DriverProfileSerializer
    
    def delete(self, request, pk):
        # pk here is user_id usually, or profile id? Let's check DriverProfileSerializer
        # The serializer uses nested fields, so we expect ID to be profile ID or user ID. 
        # For consistency with standard REST, let's assume `id` in URL is User ID or Profile ID.
        # User ID is UUID, Profile ID is Int.
        try:
            profile = DriverProfile.objects.get(user__user_id=pk)
            profile.user.delete() # Deleting user cascades to profile
            return Response({"message": "Driver deleted"})
        except DriverProfile.DoesNotExist:
             return Response({"error": "Driver not found"}, status=404)

class AdminDriverApprovalView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        """List all drivers waiting for verification"""
        pending_drivers = DriverProfile.objects.filter(admin_verified=False)
        serializer = DriverProfileSerializer(pending_drivers, many=True)
        return Response(serializer.data)

    def patch(self, request, driver_id):
        """Approve a specific driver"""
        try:
            driver_profile = DriverProfile.objects.get(user__user_id=driver_id)
            action = request.data.get('action') # 'approve' or 'reject'
            
            if action == 'approve':
                driver_profile.admin_verified = True
                driver_profile.is_active = True
                driver_profile.save()
                
                # Notify
                Notification.objects.create(
                    title="Driver Approved",
                    message=f"Driver {driver_profile.user.full_name} has been approved.",
                    user=driver_profile.user
                )
                
                return Response({"message": f"Driver {driver_profile.user.full_name} approved."})
            
            elif action == 'reject':
                return Response({"message": "Driver rejected."})
                
        except DriverProfile.DoesNotExist:
            return Response({"error": "Driver not found"}, status=404)

class AdminTripListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Ride.objects.all().order_by('-created_at')
    serializer_class = AdminRideListSerializer

class AdminTransactionListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Transaction.objects.filter(status='SUCCESS').order_by('-created_at')
    serializer_class = AdminTransactionSerializer

class AdminNotificationListView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer

class AdminPriceConfigView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        configs = PriceConfig.objects.all()
        serializer = PriceConfigSerializer(configs, many=True)
        return Response(serializer.data)
        
    def post(self, request):
        serializer = PriceConfigSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class AdminReviewUpdateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, update_id):
        pending = PendingDriverUpdate.objects.get(id=update_id)
        driver_prof = pending.driver
        driver_prof.save()
        pending.delete() 
        return Response({"message": "Profile updates applied."})