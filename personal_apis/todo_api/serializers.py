from rest_framework import serializers

from todo_api import models


class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for the ``Task`` model.
    """

    class Meta:
        fields = ('id', 'user', 'title', 'description', 'done')
        model = models.Task
