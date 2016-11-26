from rest_framework.reverse import reverse

from todo_api.models import Task


def test_create(user_factory):
    """
    Test creating a task.

    Tasks should be created with a user, title, and description.
    """
    user = user_factory()
    title = 'Test Task'
    description = 'Test task description.'

    task = Task.objects.create(
        description=description,
        title=title,
        user=user)

    assert not task.done


def test_get_absolute_url(task_factory):
    """
    Test getting the URL of a task.

    Getting the URL of a task should return the URL of that task's
    detail view.
    """
    task = task_factory()

    expected = reverse('todo-api:task-detail', kwargs={'pk': task.pk})

    assert task.get_absolute_url() == expected


def test_string_conversion(task_factory):
    """
    Test converting a task to a string.

    Converting a task to a string should return the task's title.
    """
    task = task_factory()

    assert str(task) == task.title
