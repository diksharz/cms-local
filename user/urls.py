from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserExportView

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('', include(router.urls)),
    path('details/', UserViewSet.as_view({'get': 'details'}), name='user-details'),  # Custom endpoint for user details
    path('export/', UserExportView.as_view(), name='user-export'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]


