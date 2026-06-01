import random
import string

def generate_random_code(prefix: str, length: int = 6) -> str:
    """
    Generates a code with standard random uppercase alphanumeric characters.
    E.g. WH-A1B2C3
    """
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(random.choices(chars, k=length))
    return f"{prefix}-{random_part}"
