from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet

from todo_api import models, serializers


class TaskViewSet(ModelViewSet):
    """
    View set for viewing and editing tasks.
    """
    model = models.Task
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.TaskSerializer

    def get_queryset(self):
        """
        Return the tasks owned by the current user.

        Returns:
            The tasks owned by the current user.
        """
        return models.Task.objects.filter(user=self.request.user)

    def perform_create(self, serializer: serializers.TaskSerializer):
        """
        Create a new task.

        Args:
            serializer:
                The serializer to create a task from.

        Returns:
            None
        """
        serializer.save(user=self.request.user)
