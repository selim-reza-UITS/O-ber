from rest_framework import permissions

class IsDriver(permissions.BasePermission):
    """
    Allows access only to users marked as drivers.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.is_driver
        )

class IsRider(permissions.BasePermission):
    """
    Allows access only to users marked as riders.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.is_rider
        )

class IsVerifiedDriver(permissions.BasePermission):
    """
    Ensures the driver has been approved by the Admin.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.is_driver and 
            request.user.driver_profile.admin_verified
        )