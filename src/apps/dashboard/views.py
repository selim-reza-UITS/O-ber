from django.db.models import Sum
from src.apps.payments.models import Transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import TermsAndConditionsModel, PrivacyAndPolicyModel, AboutUs, HelpSupport
from .serializers import TermsSerializer, PrivacySerializer, AboutUsSerializer, HelpSupportSerializer
from src.apps.accounts.models import DriverProfile, User,PendingDriverUpdate
from src.apps.accounts.serializers_driver import DriverProfileSerializer
from src.apps.accounts.services import SupportService

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
            # Save to database
            support_instance = serializer.save(user=request.user)
            
            # Send Email to Admin
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

class AdminEarningsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        total_revenue = Transaction.objects.filter(status='SUCCESS').aggregate(Sum('amount'))['amount__sum'] or 0
        total_rides = Transaction.objects.filter(status='SUCCESS').count()
        
        return Response({
            "total_revenue": total_revenue,
            "total_completed_rides": total_rides,
            "currency": "USD/AWG"
        })
    
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
            # Note: driver_id here is the User PK (ShortUUID)
            driver_profile = DriverProfile.objects.get(user__user_id=driver_id)
            
            action = request.data.get('action') # 'approve' or 'reject'
            
            if action == 'approve':
                driver_profile.admin_verified = True
                driver_profile.is_active = True
                driver_profile.save()
                return Response({"message": f"Driver {driver_profile.user.full_name} approved."})
            
            elif action == 'reject':
                # Optional: Send an email/notification why
                return Response({"message": "Driver rejected."})
                
        except DriverProfile.DoesNotExist:
            return Response({"error": "Driver not found"}, status=404)
        

class AdminReviewUpdateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, update_id):
        pending = PendingDriverUpdate.objects.get(id=update_id)
        driver_prof = pending.driver
        
        # Apply the pending changes to the real profile
        driver_prof.vehicle_brand = pending.vehicle_brand or driver_prof.vehicle_brand
        driver_prof.vehicle_model = pending.vehicle_model or driver_prof.vehicle_model
        # ... repeat for other fields ...
        
        driver_prof.save()
        pending.delete() # Remove the request once applied
        
        return Response({"message": "Profile updates applied."})