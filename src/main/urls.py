from django.urls import path
from django.conf.urls.static import static

from src.recorder import settings
from src.main import views

urlpatterns = [
    path('', views.index, name='index'),
    path('info', views.info, name='info'),
]

# Serve media content
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
