from django.conf import settings
from django.db import models
from rest_framework.reverse import reverse


class Task(models.Model):
    """
    Model representing a task to be completed.

    A task has a title and description, and it can be marked as
    completed.
    """
    description = models.TextField()
    done = models.BooleanField(default=False)
    title = models.CharField(max_length=255)
    user = models.ForeignKey(
        on_delete=models.CASCADE,
        to=settings.AUTH_USER_MODEL)

    def __str__(self) -> str:
        """
        Convert the task instance to a string.

        Returns:
            The task's ``title`` attribute.
        """
        return self.title

    def get_absolute_url(self) -> str:
        """
        Get the URL of the task's detail view.

        Returns:
            The URL of the task's detail view.
        """
        return reverse('todo-api:task-detail', kwargs={'pk': self.pk})
