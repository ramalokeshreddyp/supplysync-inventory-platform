import pytest
from django.urls import reverse
from rest_framework import status
from django.core.cache import cache
from apps.accounts.models import User

@pytest.mark.django_db
def test_register_user_success(api_client):
    url = reverse('auth_register')
    data = {
        "username": "newuser",
        "email": "newuser@test.com",
        "password": "Password@123",
        "full_name": "New User",
        "role": "STAFF"
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    assert "access_token" in response.data
    assert "refresh_token" in response.data
    assert response.data["username"] == "newuser"

@pytest.mark.django_db
def test_register_user_invalid_password(api_client):
    url = reverse('auth_register')
    data = {
        "username": "newuser",
        "email": "newuser@test.com",
        "password": "weak",
        "full_name": "New User"
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error_code"] == "VALIDATION_FAILED"

@pytest.mark.django_db
def test_login_success(api_client, staff_user):
    url = reverse('auth_login')
    data = {
        "email": staff_user.email,
        "password": "Password@123"
    }
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.data
    assert response.data["user_id"] == staff_user.id

@pytest.mark.django_db
def test_login_failed_increment_throttle(api_client, staff_user):
    url = reverse('auth_login')
    data = {
        "email": staff_user.email,
        "password": "WrongPassword"
    }
    
    # Reset cache
    cache.clear()
    
    # Failed attempts
    for i in range(5):
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
    # The 6th attempt should be throttled
    response = api_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data["error_code"] == "TOO_MANY_LOGIN_ATTEMPTS"

@pytest.mark.django_db
def test_logout(authenticated_staff_client):
    # Log out requires a refresh token
    url = reverse('auth_logout')
    
    # We can get a token first
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(authenticated_staff_client.handler._force_user)
    
    data = {
        "refresh_token": str(refresh)
    }
    response = authenticated_staff_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert response.data["message"] == "Successfully logged out."

@pytest.mark.django_db
def test_change_password(authenticated_staff_client):
    url = reverse('auth_change_password')
    data = {
        "old_password": "Password@123",
        "new_password": "NewSecurePassword@987"
    }
    response = authenticated_staff_client.post(url, data, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert response.data["message"] == "Password updated successfully."
