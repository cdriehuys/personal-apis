from typing import Callable

from django.contrib.auth import get_user_model

import factory

import pytest

from rest_framework.test import APIRequestFactory


class UserFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating user objects.
    """
    email = factory.LazyAttribute(lambda obj: '{user}@example.com'.format(user=obj.username))
    password = 'password'
    username = factory.Sequence(lambda n: 'user{n}'.format(n=n))

    class Meta:
        django_get_or_create = ('username',)
        model = get_user_model()

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Create a new user.
        """
        manager = cls._get_manager(model_class)

        return manager.create_user(*args, **kwargs)


@pytest.fixture(scope='module')
def api_rf() -> APIRequestFactory:
    """
    Fixture to get an instance of ``APIRequestFactory``.

    Returns:
        A new ``APIRequestFactory``.
    """
    return APIRequestFactory()


@pytest.fixture(scope='function')
def user_factory(db):
    """
    Fixture to get the ``UserFactory`` class.

    Also ensures the Django database is set up.

    Returns:
        The ``UserFactory`` class.
    """
    return UserFactory
