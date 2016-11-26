from todo_api.models import Task
from todo_api.serializers import TaskSerializer


def test_deserialize(user_factory):
    """
    Test deserializing a task.

    Given valid data, a task instance should be able to be constructed.
    """
    user = user_factory()
    data = {
        'title': 'Test Task',
        'description': 'Test task description.',
        'done': False,
    }

    serializer = TaskSerializer(data=data)

    assert serializer.is_valid()

    task = serializer.save(user=user)

    assert Task.objects.count() == 1
    assert task.user == user
    assert task.title == data['title']
    assert task.description == data['description']
    assert task.done == data['done']


def test_serialize(task_factory):
    """
    Test serializing a task.

    Serializing a task should return its JSON representation.
    """
    task = task_factory()

    serializer = TaskSerializer(task)

    expected = {
        'id': task.id,
        'user': task.user.pk,
        'title': task.title,
        'description': task.description,
        'done': task.done,
    }

    assert serializer.data == expected
