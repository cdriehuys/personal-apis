from django.contrib.auth import get_user_model

from rest_framework import serializers


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering new users.
    """
    class Meta:
        extra_kwargs = {
            'password': {
                'style': {
                    'input_type': 'password',
                },
                'write_only': True,
            },
        }
        model = get_user_model()
        fields = ('email', 'username', 'password')

    def create(self, validated_data):
        """
        Create a new user from the serializer's validated data.

        Args:
            validated_data:
                The data to create a new user with.

        Returns:
            A new user.
        """
        return get_user_model().objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            username=validated_data['username'])
