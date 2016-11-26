from django.conf.urls import include, url

from rest_framework.routers import DefaultRouter

from todo_api import views


router = DefaultRouter()
router.register(r'tasks', views.TaskViewSet, base_name='task')


urlpatterns = [
    url(r'^', include(router.urls)),
]
