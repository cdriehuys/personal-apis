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


def test_string_conversion(task_factory):
    """
    Test converting a task to a string.

    Converting a task to a string should return the task's title.
    """
    task = task_factory()

    assert str(task) == task.title
