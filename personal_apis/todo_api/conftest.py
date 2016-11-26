import factory

import pytest


class TaskFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating ``Task`` instances.
    """
    description = 'Test task description.'
    done = False
    title = factory.Sequence(lambda n: 'Test Task {n}'.format(n=n))
    user = factory.SubFactory('conftest.UserFactory')

    class Meta:
        model = 'todo_api.Task'


@pytest.fixture
def task_factory(db):
    """
    Return the ``TaskFactory`` class.

    Also ensures the Django database is set up.

    Returns:
        The ``TaskFactory`` class.
    """
    return TaskFactory
