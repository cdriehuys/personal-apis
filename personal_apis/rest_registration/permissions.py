from rest_framework.permissions import BasePermission


class IsAnonymous(BasePermission):
    """
    Permission that only allows anonymous users access.
    """

    def has_permission(self, request, view):
        """
        Determine if the given request should be permitted.

        If the current user is not authenticated, the request should
        succeed.

        Args:
            request:
                The request to check.
            view:
                The view being accessed.

        Returns:
            bool:
                ``True`` if the requesting user is anonymous, ``False``
                otherwise.
        """
        return not request.user.is_authenticated()
