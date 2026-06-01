import re
from django.core.exceptions import ValidationError

def validate_password_strength(password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    
    if not any(char.isupper() for char in password):
        raise ValidationError("Password must contain at least one uppercase letter.")
        
    if not any(char.isdigit() for char in password):
        raise ValidationError("Password must contain at least one digit.")
        
    special_chars = r"[!@#$%^&*(),.?\":{}|<>]"
    if not re.search(special_chars, password):
        raise ValidationError("Password must contain at least one special character.")
