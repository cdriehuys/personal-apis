from django.contrib.auth.hashers import check_password

import pytest

from rest_registration.serializers import UserRegistrationSerializer


@pytest.mark.django_db
def test_read_password():
    """
    Test reading the password from a serializer.

    The password field should be write-only.
    """
    data = {
        'email': 'test@example.com',
        'username': 'johndoe',
        'password': 'password',
    }
    serializer = UserRegistrationSerializer(data=data)

    expected = data.copy()
    del expected['password']

    assert serializer.is_valid()
    assert serializer.data == expected


@pytest.mark.django_db
def test_save():
    """
    Test saving a new user from serializer data.

    Saving a valid serializer should create a new user.
    """
    data = {
        'email': 'johndoe@example.com',
        'username': 'johndoe',
        'password': 'password',
    }
    serializer = UserRegistrationSerializer(data=data)

    assert serializer.is_valid()

    user = serializer.save()

    assert user.email == data['email']
    assert user.username == data['username']
    assert check_password(data['password'], user.password)


def test_validate_blank():
    """
    Test validating a blank serializer.

    A blank serializer should not be valid.
    """
    serializer = UserRegistrationSerializer(data={})

    assert not serializer.is_valid()
