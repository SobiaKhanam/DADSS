from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PersonImagesViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'face_recognition', PersonImagesViewSet, basename="face_recognition")

urlpatterns = [
    path('', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
