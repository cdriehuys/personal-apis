from django.conf.urls import url


from rest_registration import views

urlpatterns = [
    url(r'^$', views.RegistrationView.as_view(), name='register'),
]
