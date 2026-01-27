from django.urls import path,include

#third part imports:
from rest_framework_simplejwt.views import TokenRefreshView

# urls imports:
#
from src.apps.accounts.api import views as accounts
from src.apps.accounts.api import views_profile as accounts_profile
from src.apps.accounts.api import views_driver as driver_accounts
#
from src.apps.riders import views as riders
from src.apps.drivers import views as drivers
#
from src.apps.dashboard import views as dashboard

from src.apps.payments import views as payments

auth_patterns = [
    path("signup/",accounts.SignUpView.as_view(),name="signup"),
    path("login/",accounts.LoginView.as_view(),name="login"),
    path("token/refresh/",TokenRefreshView.as_view(),name="new_token_generate"),
]

password_management = [
    path("forget-password/",accounts.ForgotPasswordRequestView.as_view(),name="send_email"),
    path("verify-otp/",accounts.VerifyOTPView.as_view(),name="verify_otp"),
    path("reset_password/",accounts.PasswordResetConfirmView.as_view(),name="password_reset"),
]

rider_pattern = [
    path("accounts/profile/",accounts_profile.UserProfileView.as_view(),name="Profile"),
    path("ride/estimate/",riders.FareEstimateView.as_view(),name="fare_estimate"),
    path("ride/create/",riders.CreateRideView.as_view(),name="request_for_a_ride"),
    path("ride/history/",riders.RideHistoryView.as_view(),name="all_ride_history"),
    path("ride/<int:ride_id>/",riders.RideDetailView.as_view(),name="ride_detail"),
    path("ride/<int:ride_id>/cancel/",riders.CancelRideView.as_view(),name="cancel_ride"),
    path("ride/<int:ride_id>/review/",riders.RideReviewView.as_view(),name="review_ride"),
    # Payment
    path("payment/config/", payments.StripeConfigView.as_view(), name="stripe-config"),
    path("payment/sheet/", payments.PaymentSheetView.as_view(), name="payment-sheet"),
    path("payment/webhook/", payments.StripeWebhookView.as_view(), name="stripe-webhook"),
]

# rider_websocket_pattern = []

driver_pattern = [
    path("driver-onboarding/",driver_accounts.DriverOnboardingView.as_view(),name="onboarding"),
    path("verify-KYC/",driver_accounts.DriverSelfieVerifyView.as_view(),name="match-selfie"),
    path("location-update/",drivers.UpdateDriverLocationView.as_view(),name="location_update"),
    path("available-for-rides/",drivers.AvailableRidesView.as_view(),name="check all available rider list"),
    path("accept-ride/<int:ride_id>/",drivers.AcceptRideView.as_view(),name="accept_riders"),
    path('toggle-online/', drivers.DriverToggleOnlineView.as_view(), name='driver-toggle-online'),
    path('dashboard/',drivers.DriverProfileDashboardView.as_view(),name="driver_profile"),
    path('earnings/',drivers.DriverEarningsView.as_view(),name="driver_earnings"),
    path('trip-history/',drivers.DriverTripHistoryView.as_view(),name="driver_trip_history"),
    path('ride-status/<int:ride_id>/', payments.UpdateRideStatusView.as_view(), name='update_ride_status'),
]

dashboard_patterns = [
    path("terms-and-conditions/",dashboard.TermsView.as_view(),name="terms-and-conditions"),
    path("privacy-and-policy/",dashboard.PrivacyView.as_view(),name="privacy-and-policy"),
    path("about-us/",dashboard.AboutUsView.as_view(),name="aboutUs"),
    path("help-and-support/",dashboard.HelpSupportView.as_view(),name="helpAndSupport"),
    
    # Admin API
    path("admin/stats/", dashboard.AdminDashboardStatsView.as_view(), name="admin_stats"),
    path("admin/users/", dashboard.AdminUserListView.as_view(), name="admin_users"),
    path("admin/users/<str:pk>/", dashboard.AdminUserListView.as_view(), name="admin_user_detail"),
    path("admin/drivers/", dashboard.AdminDriverListView.as_view(), name="admin_drivers"),
    path("admin/drivers/<str:pk>/", dashboard.AdminDriverListView.as_view(), name="admin_driver_detail"),
    path("admin/approve-driver/<str:driver_id>/",dashboard.AdminDriverApprovalView.as_view(),name="approveDriver"), # PATCH
    path("admin/new-driver-requests/",dashboard.AdminDriverApprovalView.as_view(),name="newDriverRequests"), # GET
    path("admin/trips/", dashboard.AdminTripListView.as_view(), name="admin_trips"),
    path("admin/transactions/", dashboard.AdminTransactionListView.as_view(), name="admin_transactions"),
    path("admin/notifications/", dashboard.AdminNotificationListView.as_view(), name="admin_notifications"),
    path("admin/pricing/", dashboard.AdminPriceConfigView.as_view(), name="admin_pricing"),
    path("admin/pricing/<int:pk>/", dashboard.AdminPriceConfigView.as_view(), name="admin_pricing_detail"),
    path("admin/profile/", dashboard.AdminProfileView.as_view(), name="admin_profile"),
    path("admin/password/", dashboard.AdminPasswordUpdateView.as_view(), name="admin_password"),
]

urlpatterns = [
    path("auth/",include(auth_patterns)),
    path("password/management/",include(password_management)),
    path("rider/",include(rider_pattern)),
    path("drivers/",include(driver_pattern)),
    path("platform/",include(dashboard_patterns)),
]
