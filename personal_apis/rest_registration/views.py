from django.contrib.auth import get_user_model

from rest_framework.generics import CreateAPIView

from rest_registration import serializers
from rest_registration.permissions import IsAnonymous


class RegistrationView(CreateAPIView):
    """
    View for registering new users.
    """
    model = get_user_model()
    permission_classes = (IsAnonymous,)
    serializer_class = serializers.UserRegistrationSerializer
