from rest_framework import serializers

from todo_api import models


class TaskSerializer(serializers.ModelSerializer):
    """
    Serializer for the ``Task`` model.
    """

    class Meta:
        extra_kwargs = {
            'user': {
                'read_only': True,
            },
        }
        fields = ('id', 'user', 'title', 'description', 'done')
        model = models.Task
