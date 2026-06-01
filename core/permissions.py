from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    message = "Access restricted to Administrators only."

    def has_permission(self, request, view):
        return (
            request.user 
            and request.user.is_authenticated 
            and (request.user.role == 'ADMIN' or request.user.is_superuser)
        )

class IsWarehouseManagerOrAdmin(BasePermission):
    message = "Access restricted to Warehouse Managers and Administrators."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.role in ['ADMIN', 'WAREHOUSE_MANAGER'] or request.user.is_superuser

class IsProcurementManagerOrAdmin(BasePermission):
    message = "Access restricted to Procurement Managers and Administrators."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.role in ['ADMIN', 'PROCUREMENT_MANAGER'] or request.user.is_superuser

class IsWarehouseManagerOrAdminOrStaff(BasePermission):
    message = "Access restricted to Warehouse Managers, Staff, and Administrators."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.role in ['ADMIN', 'WAREHOUSE_MANAGER', 'STAFF'] or request.user.is_superuser

class IsWarehouseManagerOrAdminOrProcurementManager(BasePermission):
    message = "Access restricted to Warehouse Managers, Procurement Managers, and Administrators."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.role in ['ADMIN', 'WAREHOUSE_MANAGER', 'PROCUREMENT_MANAGER'] or request.user.is_superuser

class IsOwnerOrAdmin(BasePermission):
    message = "Access restricted to the owner of this record or Administrators."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role == 'ADMIN' or request.user.is_superuser:
            return True
        
        # Look for owner indicators dynamically
        created_by = getattr(obj, 'created_by', None)
        performed_by = getattr(obj, 'performed_by', None)
        user_field = getattr(obj, 'user', None)

        if created_by == request.user:
            return True
        if performed_by == request.user:
            return True
        if user_field == request.user:
            return True
            
        return False
