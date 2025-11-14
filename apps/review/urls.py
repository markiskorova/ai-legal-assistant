from django.urls import path
from .views import ReviewRunView

urlpatterns = [
    path('run', ReviewRunView.as_view(), name='review-run'),
]
