from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIRequestFactory

from todo_api import models
from todo_api import serializers
from todo_api.views import TaskViewSet


def test_create_task(api_rf: APIRequestFactory, user_factory):
    """
    Test creating a task.

    Submitting valid data through a POST request should create a new
    task.
    """
    user = user_factory()
    data = {
        'title': 'Test Title',
        'description': 'Test task description.',
    }

    url = reverse('todo-api:task-list')
    request = api_rf.post(url, data)
    request.user = user

    response = TaskViewSet.as_view({'post': 'create'})(request)

    assert response.status_code == status.HTTP_201_CREATED

    task = models.Task.objects.get()
    serializer = serializers.TaskSerializer(task)

    assert response.data == serializer.data
    assert task.user == user


def test_delete_task(api_rf: APIRequestFactory, task_factory):
    """
    Test deleting a task.

    Sending a DELETE request to a task's detail view should delete that
    task.
    """
    task = task_factory()

    url = task.get_absolute_url()
    request = api_rf.delete(url)
    request.user = task.user

    response = TaskViewSet.as_view({'delete': 'destroy'})(request, pk=task.pk)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert models.Task.objects.count() == 0


def test_detail_view(api_rf: APIRequestFactory, task_factory):
    """
    Test the task detail view.

    Sending a GET request to the task detail view should return the
    serialized version of that task.
    """
    task = task_factory()

    serializer = serializers.TaskSerializer(task)

    url = task.get_absolute_url()
    request = api_rf.get(url)
    request.user = task.user

    response = TaskViewSet.as_view({'get': 'retrieve'})(request, pk=task.pk)

    assert response.status_code == status.HTTP_200_OK
    assert response.data == serializer.data


def test_list_tasks(api_rf: APIRequestFactory, task_factory, user_factory):
    """
    Test the task list view.

    The list view should only list tasks owned by the current user.
    """
    user1 = user_factory()
    user2 = user_factory()

    task_factory(user=user1)
    task_factory(user=user1)
    task_factory(user=user2)

    serializer = serializers.TaskSerializer(models.Task.objects.filter(user=user1), many=True)

    url = reverse('todo-api:task-list')
    request = api_rf.get(url)
    request.user = user1

    response = TaskViewSet.as_view({'get': 'list'})(request)

    assert response.status_code == status.HTTP_200_OK
    assert response.data == serializer.data


def test_patch_task(api_rf: APIRequestFactory, task_factory):
    """
    Test partially updating a task.

    Sending a PATCH request should allow for partial updates of a task.
    """
    task = task_factory()
    data = {
        'description': 'My new task description.',
    }

    url = task.get_absolute_url()
    request = api_rf.patch(url, data)
    request.user = task.user

    response = TaskViewSet.as_view({'patch': 'partial_update'})(request, pk=task.pk)

    task.refresh_from_db()
    serializer = serializers.TaskSerializer(task)

    assert response.status_code == status.HTTP_200_OK
    assert response.data == serializer.data
    assert task.description == data['description']


def test_unauthenticated(api_rf: APIRequestFactory):
    """
    Test an unauthenticated request to the view.

    If the user is not authenticated, they should receive a permission
    denied error.
    """
    url = reverse('todo-api:task-list')
    request = api_rf.get(url)

    response = TaskViewSet.as_view({'get': 'list'})(request)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_task(api_rf: APIRequestFactory, task_factory):
    """
    Test updating a task.

    Sending an PUT request to a task's detail view should update that
    task.
    """
    task = task_factory()
    data = {
        'title': 'My New Task Title',
        'description': 'My new awesome description.',
        'done': True,
    }

    url = task.get_absolute_url()
    request = api_rf.put(url, data)
    request.user = task.user

    response = TaskViewSet.as_view({'put': 'update'})(request, pk=task.pk)

    task.refresh_from_db()
    serializer = serializers.TaskSerializer(task)

    assert response.status_code == status.HTTP_200_OK
    assert response.data == serializer.data
    assert task.title == data['title']
    assert task.description == data['description']
    assert task.done == data['done']
