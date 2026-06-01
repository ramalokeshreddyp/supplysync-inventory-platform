import logging
from django.utils import timezone
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

class ResourceNotFoundException(APIException):
    status_code = 404
    default_detail = 'The requested resource was not found.'
    default_code = 'RESOURCE_NOT_FOUND'

class DuplicateResourceException(APIException):
    status_code = 409
    default_detail = 'A resource with these details already exists.'
    default_code = 'DUPLICATE_RESOURCE'

class InsufficientInventoryException(APIException):
    status_code = 422
    default_detail = 'Insufficient inventory available for the operation.'
    default_code = 'INSUFFICIENT_INVENTORY'

class InvalidOperationException(APIException):
    status_code = 422
    default_detail = 'The requested operation is invalid.'
    default_code = 'INVALID_OPERATION'

def custom_exception_handler(exc, context):
    # Call DRF's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)
    
    request = context.get('request')
    path = request.path if request else ''
    timestamp = timezone.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    if response is not None:
        status_code = response.status_code
        
        # Determine the error code
        if isinstance(exc, ValidationError):
            error_code = 'VALIDATION_FAILED'
            message = 'Validation failed.'
        elif response.status_code == 429:
            error_code = 'TOO_MANY_LOGIN_ATTEMPTS'
            message = getattr(exc, 'detail', 'Too many login attempts.')
            if isinstance(message, dict) and 'detail' in message:
                message = str(message['detail'])
        else:
            error_code = getattr(exc, 'default_code', 'ERROR')
            # If the exception has a code on the detail object, use it
            if hasattr(exc, 'detail') and isinstance(exc.detail, dict) and 'code' in exc.detail:
                error_code = str(exc.detail['code']).upper()
            elif hasattr(exc, 'detail') and hasattr(exc.detail, 'code'):
                error_code = str(exc.detail.code).upper()
            
            # Use detail as message if it is string/dict
            if hasattr(exc, 'detail') and isinstance(exc.detail, dict) and 'detail' in exc.detail:
                message = str(exc.detail['detail'])
            elif hasattr(exc, 'detail') and isinstance(exc.detail, dict) and 'message' in exc.detail:
                message = str(exc.detail['message'])
            elif hasattr(exc, 'detail') and isinstance(exc.detail, str):
                message = exc.detail
            else:
                message = getattr(exc, 'default_detail', str(exc))

        # Format errors for validation
        errors = []
        if isinstance(exc, ValidationError):
            if isinstance(exc.detail, dict):
                for field, field_errors in exc.detail.items():
                    if isinstance(field_errors, list):
                        for err in field_errors:
                            errors.append({
                                "field": str(field),
                                "message": str(err)
                            })
                    else:
                        errors.append({
                            "field": str(field),
                            "message": str(field_errors)
                        })
            elif isinstance(exc.detail, list):
                for err in exc.detail:
                    errors.append({
                        "field": "non_field_errors",
                        "message": str(err)
                    })
            else:
                errors.append({
                    "field": "non_field_errors",
                    "message": str(exc.detail)
                })

        custom_data = {
            "timestamp": timestamp,
            "status": status_code,
            "error_code": error_code,
            "message": message,
            "path": path,
            "errors": errors
        }
        
        # Copy any additional keys from exc.detail dict to custom_data (e.g. short_items)
        if hasattr(exc, 'detail') and isinstance(exc.detail, dict):
            for k, v in exc.detail.items():
                if k not in ['detail', 'message', 'errors']:
                    custom_data[k] = v
        
        response.data = custom_data
        return response

    # Handle unhandled system exceptions (HTTP 500)
    logger.exception("Unhandled server exception occurred: %s", exc)
    
    custom_data = {
        "timestamp": timestamp,
        "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "error_code": "INTERNAL_SERVER_ERROR",
        "message": "An internal server error occurred.",
        "path": path,
        "errors": []
    }
    
    return Response(custom_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
