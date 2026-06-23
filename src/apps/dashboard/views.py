from django.db.models import Sum, Count, F
from django.db.models.functions import TruncMonth, TruncYear
from src.apps.payments.models import Transaction, Withdrawal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics
from rest_framework.pagination import PageNumberPagination
from .models import Marketing, TermsAndConditionsModel, PrivacyAndPolicyModel, AboutUs, HelpSupport, PriceConfig, Notification, Commision
from .serializers import (
    MarketingSerializer, TermsSerializer, PrivacySerializer, AboutUsSerializer, HelpSupportSerializer,
    PriceConfigSerializer, NotificationSerializer, AdminUserListSerializer,
    AdminTransactionSerializer, AdminRideListSerializer, AdminProfileSerializer,
    AdminPasswordUpdateSerializer, AdminDriverListSerializer, DriverDetailSerializer, AdminRideDetailSerializer, CashWithdrawSerializer, CommisionSerializer, BlockSerilaizer,
    AdminPaymentSerializer
)
from src.apps.accounts.models import DriverProfile, User, PendingDriverUpdate
from src.apps.accounts.serializers_driver import DriverProfileSerializer
from src.apps.accounts.services import SupportService
from src.apps.riders.models import Ride
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
import stripe
from django.conf import settings

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


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
        current_date = timezone.now()
        last_month_start = (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
        
        # 1. Totals - Current Month
        total_revenue = Transaction.objects.filter(status='SUCCESS', created_at__month=current_date.month, created_at__year=current_date.year).aggregate(Sum('amount'))['amount__sum'] or 0
        total_users = User.objects.filter(is_rider=True, date_joined__month=current_date.month, date_joined__year=current_date.year).count()
        total_drivers = DriverProfile.objects.filter(admin_verified=True, created_at__month=current_date.month, created_at__year=current_date.year).count()
        new_driver_requests = DriverProfile.objects.filter(admin_verified=False).count()

        # Calculate Previous Month Totals for Percentage Change
        last_revenue = Transaction.objects.filter(status='SUCCESS', created_at__month=last_month_start.month, created_at__year=last_month_start.year).aggregate(Sum('amount'))['amount__sum'] or 0
        last_users = User.objects.filter(is_rider=True, date_joined__month=last_month_start.month, date_joined__year=last_month_start.year).count()
        last_drivers = DriverProfile.objects.filter(admin_verified=True, created_at__month=last_month_start.month, created_at__year=last_month_start.year).count()
        
        # Calculate Percentage Changes
        revenue_change = 0 if last_revenue == 0 else round(((total_revenue - last_revenue) / last_revenue) * 100, 2) if last_revenue > 0 else 0
        users_change = 0 if last_users == 0 else round(((total_users - last_users) / last_users) * 100, 2) if last_users > 0 else 0
        drivers_change = 0 if last_drivers == 0 else round(((total_drivers - last_drivers) / last_drivers) * 100, 2) if last_drivers > 0 else 0
        requests_change = 0

        # 2. Growth (User) - Group by Month
        user_growth_qs = User.objects.filter(is_rider=True)
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
                "revenue": {
                    "value": int(total_revenue) if total_revenue else 0,
                    "change_percent": revenue_change
                },
                "users": {
                    "value": total_users,
                    "change_percent": users_change
                },
                "drivers": {
                    "value": total_drivers,
                    "change_percent": drivers_change
                },
                "new_driver_requests": {
                    "value": new_driver_requests,
                    "change_percent": requests_change
                }
            },
            "growth": {
                "users": user_growth,
                "revenue": revenue_growth
            }
        })
    




class SearchUsersListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminUserListSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        queryset = User.objects.all().order_by('-date_joined')
        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone_number__icontains=query)
            )
        return queryset




class AdminUserListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserListSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class AdminUserDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()
    serializer_class = AdminUserListSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        return User.objects.filter(is_driver=False)

    def delete(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            user.delete()
            return Response({"message": "User deleted"}, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        


    


class NormalUserList(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.filter(is_driver=False)
    serializer_class = AdminUserListSerializer





class AdminDriverListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = DriverProfile.objects.all()
    serializer_class = AdminDriverListSerializer


class AdminDriverDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = DriverProfile.objects.all()
    serializer_class = DriverDetailSerializer
    lookup_field = 'user__user_id'
    lookup_url_kwarg = 'pk'


    def delete(self, request, *args, **kwargs):
        try:
            profile = self.get_object()
            profile.user.delete()
            return Response({"message": "Driver deleted"}, status=status.HTTP_204_NO_CONTENT)
        except DriverProfile.DoesNotExist:
            return Response({"error": "Driver not found"}, status=status.HTTP_404_NOT_FOUND)



class AdminDriverApprovalView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        pending_drivers = DriverProfile.objects.filter(admin_verified=False, is_rejected=False)
        serializer = AdminDriverListSerializer(pending_drivers, many=True, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, driver_id):
        """Approve or reject a specific driver"""
        try:
            driver_profile = DriverProfile.objects.get(user__user_id=driver_id)
            action = request.data.get('action') # 'approve' or 'reject'
            
            if action == 'approve':
                driver_profile.admin_verified = True
                driver_profile.is_active = True
                driver_profile.is_rejected = False
                driver_profile.save()
                
                # Notify
                Notification.objects.create(
                    title="Driver Approved",
                    message=f"Driver {driver_profile.user.full_name} has been approved.",
                    user=driver_profile.user
                )
                
                serializer = DriverDetailSerializer(driver_profile)
                return Response({
                    "message": f"Driver {driver_profile.user.full_name} approved.",
                    "data": serializer.data
                })
            
            elif action == 'reject':
                driver_profile.is_rejected = True
                driver_profile.admin_verified = False
                driver_profile.is_active = False
                driver_profile.save()
                
                # Notify
                Notification.objects.create(
                    title="Driver Application Rejected",
                    message=f"Your driver application has been rejected.",
                    user=driver_profile.user
                )
                
                serializer = DriverDetailSerializer(driver_profile)
                return Response({
                    "message": f"Driver {driver_profile.user.full_name} rejected.",
                    "data": serializer.data
                }, status=status.HTTP_200_OK)
                
        except DriverProfile.DoesNotExist:
            return Response({"error": "Driver not found"}, status=404)

class AdminTripListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Ride.objects.all().order_by('-created_at')
    serializer_class = AdminRideListSerializer


class AdminTripDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Ride.objects.all()
    serializer_class = AdminRideDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'ride_id'


class TripTrackingByDriverView(generics.ListAPIView):
    """Admin can see driver's full ride history"""
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminRideListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        driver_id = self.kwargs.get('driver_id')
        try:
            # Get User object from user_id
            user = User.objects.get(user_id=driver_id)
            return Ride.objects.filter(driver=user).order_by('-created_at')
        except User.DoesNotExist:
            return Ride.objects.none()

    def list(self, request, *args, **kwargs):
        driver_id = self.kwargs.get('driver_id')
        try:
            # Get User object from user_id
            user = User.objects.get(user_id=driver_id)
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                "message": f"Trip history for driver {user.full_name}",
                "driver_id": user.user_id,
                "driver_name": user.full_name,
                "total_trips": queryset.count(),
                "data": serializer.data
            })
        except User.DoesNotExist:
            return Response({"error": "Driver not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class AdminTransactionListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Transaction.objects.filter(status='SUCCESS').order_by('-created_at')
    serializer_class = AdminTransactionSerializer


class AdminTransactionDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Transaction.objects.all()
    serializer_class = AdminTransactionSerializer
    lookup_field = 'pk'

class AdminNotificationListView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer


class AdminNotificationDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    lookup_field = 'pk'

class AdminPriceConfigView(APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, pk=None):
        if pk:
            try:
                config = PriceConfig.objects.get(pk=pk)
                serializer = PriceConfigSerializer(config)
                return Response(serializer.data)
            except PriceConfig.DoesNotExist:
                return Response({"error": "Config not found"}, status=404)
        configs = PriceConfig.objects.all()
        serializer = PriceConfigSerializer(configs, many=True)
        return Response(serializer.data)
        
    def post(self, request):
        serializer = PriceConfigSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def patch(self, request, pk):
        try:
            config = PriceConfig.objects.get(pk=pk)
            serializer = PriceConfigSerializer(config, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except PriceConfig.DoesNotExist:
            return Response({"error": "Config not found"}, status=404)

    def delete(self, request, pk):
        try:
            config = PriceConfig.objects.get(pk=pk)
            config.delete()
            return Response({"message": "Pricing config deleted"})
        except PriceConfig.DoesNotExist:
            return Response({"error": "Config not found"}, status=404)

class AdminReviewUpdateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, update_id):
        pending = PendingDriverUpdate.objects.get(id=update_id)
        driver_prof = pending.driver
        driver_prof.save()
        pending.delete() 
        return Response({"message": "Profile updates applied."})


class AdminProfileView(APIView):
    """Admin can view and update their own profile (name only)"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        serializer = AdminProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = AdminProfileSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminPasswordUpdateView(APIView):
    """Admin can update their password"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = AdminPasswordUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({"message": "Password updated successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminBlockUnblockUserView(APIView):

    permission_classes = [permissions.IsAdminUser]
    serializer_class = BlockSerilaizer

    def patch(self, request, user_id):
        try:
            user = User.objects.get(user_id=user_id)
            is_blocked = request.data.get('is_blocked', user.is_blocked)
            reason = request.data.get('reason', '')
            
            if isinstance(is_blocked, str):
                is_blocked = is_blocked.lower() in ['true', '1', 'yes']
            
            user.is_blocked = is_blocked
            user.is_active = not is_blocked
            user.save()
            
            # Create notification
            if is_blocked:
                Notification.objects.create(
                    user=user,
                    title="Account Blocked",
                    message=f"Your account has been blocked. Reason: {reason}" if reason else "Your account has been blocked."
                )
            else:
                Notification.objects.create(
                    user=user,
                    title="Account Unblocked",
                    message="Your account has been unblocked."
                )
            
            return Response({"message": "User Blocked status updated.", "data": BlockSerilaizer(user).data})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)



class CashWithdrawView(generics.CreateAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CashWithdrawSerializer

    def create(self, request, *args, **kwargs):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)        
        user = request.user
        amount = serializer.validated_data['amount']
        currency = serializer.validated_data['currency']
        destination_account = serializer.validated_data['destination_account']
        transfer_group = serializer.validated_data.get('transfer_group', '')
        
        # Check if user has sufficient balance
        if float(user.wallet_balance) < float(amount):
            return Response(
                {"error": "Insufficient wallet balance"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create Stripe transfer
            transfer = stripe.Transfer.create(
                amount=int(amount * 100),  # Convert to cents
                currency=currency.lower(),
                destination=destination_account,
                transfer_group=transfer_group if transfer_group else f"WITHDRAWAL_{user.user_id}_{timezone.now().timestamp()}"
            )
            
            # If transfer successful, create Withdrawal record
            withdrawal = Withdrawal.objects.create(
                user=user,
                amount=amount,
                currency=currency,
                destination_account=destination_account,
                transfer_group=transfer_group,
                stripe_transfer_id=transfer['id'],
                status='SUCCESS'
            )
            
            # Deduct amount from user's wallet balance
            user.wallet_balance = float(user.wallet_balance) - float(amount)
            user.save()
            
            return Response({
                "message": "Withdrawal successful",
                "withdrawal_id": withdrawal.id,
                "stripe_transfer_id": transfer['id'],
                "amount": str(amount),
                "currency": currency,
                "remaining_balance": str(user.wallet_balance),
                "status": "SUCCESS"
            }, status=status.HTTP_201_CREATED)
            
        except stripe.error.InvalidRequestError as e:
            return Response(
                {"error": f"Invalid Stripe request: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except stripe.error.AuthenticationError as e:
            return Response(
                {"error": "Authentication error with Stripe"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except stripe.error.StripeError as e:
            # Create failed withdrawal record
            Withdrawal.objects.create(
                user=user,
                amount=amount,
                currency=currency,
                destination_account=destination_account,
                transfer_group=transfer_group,
                status='FAILED'
            )
            return Response(
                {"error": f"Stripe error: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Error processing withdrawal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        


class CommisionListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Commision.objects.all().order_by('-created_at')
    serializer_class = CommisionSerializer
    
    def perform_create(self, serializer):
        serializer.save()


class CommisionDetailsandDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = Commision.objects.all()
    serializer_class = CommisionSerializer
    lookup_field = 'pk'
    
    def perform_update(self, serializer):
        serializer.save()



class MarketingListCreateView(generics.ListCreateAPIView):
    queryset = Marketing.objects.all().order_by('-created_at')
    serializer_class = MarketingSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class MarketingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Marketing.objects.all()
    serializer_class = MarketingSerializer
    lookup_field = 'pk'

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class AdminPaymentListView(generics.ListAPIView):
    """
    Admin: list every payment made on the platform (one row per ride).

    Optional query params:
      ?status=SUCCESS|PENDING|FAILED   -> filter by payment status
      ?payment_method=CASH|CARD        -> filter by how the rider paid
      ?search=<text>                   -> match ride id / driver / rider name
      ?page=<n>&page_size=<n>          -> pagination
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminPaymentSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = (
            Transaction.objects
            .select_related('ride', 'ride__driver', 'ride__rider')
            .order_by('-created_at')
        )
        params = self.request.query_params

        status_param = params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())

        method = params.get('payment_method')
        if method:
            qs = qs.filter(ride__payment_method=method.upper())

        search = params.get('search')
        if search:
            qs = qs.filter(
                Q(ride__id__icontains=search) |
                Q(ride__driver__full_name__icontains=search) |
                Q(ride__rider__full_name__icontains=search)
            )
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        total_amount = (
            queryset.filter(status='SUCCESS').aggregate(Sum('amount'))['amount__sum'] or 0
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['total_successful_amount'] = str(total_amount)
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'total_successful_amount': str(total_amount),
            'results': serializer.data,
        })


class AdminPaymentDetailView(generics.RetrieveDestroyAPIView):
    """
    Admin: retrieve a single payment, or DELETE it (the "User Delete" action
    from the spec). Deleting only removes the Transaction record; the Ride is
    left intact.
    """
    permission_classes = [permissions.IsAdminUser]
    queryset = Transaction.objects.select_related(
        'ride', 'ride__driver', 'ride__rider'
    ).all()
    serializer_class = AdminPaymentSerializer
    lookup_field = 'pk'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        ride_id = instance.ride_id
        self.perform_destroy(instance)
        return Response(
            {'message': f'Payment for ride {ride_id} deleted.'},
            status=status.HTTP_200_OK,
        )


class AdminUserDeleteView(generics.DestroyAPIView):
    """
    Admin: delete ANY user (rider OR driver) by their user_id.

    Deleting the User cascades to their RiderProfile / DriverProfile and
    related rows (both profiles use on_delete=CASCADE). Rides they took as a
    rider are removed (Ride.rider is CASCADE); rides they drove are kept but
    have the driver set to NULL (Ride.driver is SET_NULL).

    Guard rails: an admin cannot delete their own account, nor any
    staff/superuser account, through this endpoint.
    """
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()
    serializer_class = AdminUserListSerializer
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        if user == request.user:
            return Response(
                {"error": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.is_staff or user.is_superuser:
            return Response(
                {"error": "Staff/admin accounts cannot be deleted from this endpoint."},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_id = user.user_id
        full_name = user.full_name
        role = "driver" if user.is_driver else "rider"
        user.delete()
        return Response(
            {"message": f"{role.capitalize()} '{full_name}' (ID: {user_id}) deleted."},
            status=status.HTTP_200_OK,
        )