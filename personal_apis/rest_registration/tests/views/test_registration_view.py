from django.contrib.auth import get_user_model

import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIRequestFactory

from conftest import UserFactory
from rest_registration import serializers
from rest_registration.views import RegistrationView


def test_authenticated(api_rf: APIRequestFactory, user_factory: UserFactory):
    """
    Test using the view as an authenticated user.

    If an authenticated user attempts to register a new user, they
    should receive a permission denied error.
    """
    data = {
        'email': 'johndoe@example.com',
        'password': 'password',
        'username': 'johndoe',
    }
    user = user_factory()

    url = reverse('rest-registration:register')
    request = api_rf.post(url, data)
    request.user = user

    response = RegistrationView.as_view()(request)

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get(api_rf: APIRequestFactory):
    """
    Test a GET request to the view.

    A GET request to the registration view should return a 405
    response.
    """
    url = reverse('rest-registration:register')
    request = api_rf.get(url)

    response = RegistrationView.as_view()(request)

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
def test_register_user(api_rf: APIRequestFactory):
    """
    Test registering a new user.

    Sending a POST request with valid data to the view should create a
    new user.
    """
    data = {
        'email': 'johndoe@example.com',
        'password': 'password',
        'username': 'johndoe',
    }

    url = reverse('rest-registration:register')
    request = api_rf.post(url, data)

    serializer = serializers.UserRegistrationSerializer(data=data)
    assert serializer.is_valid()

    response = RegistrationView.as_view()(request)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data == serializer.data

    assert get_user_model().objects.count() == 1
