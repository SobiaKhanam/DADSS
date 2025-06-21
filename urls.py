"""dadss_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('users.urls')),
    path('', include('main.urls')),
    path('', include('vis.vis_urls')),
    path('', include('ais.ais_urls')),
    path('', include('intel.intel_urls')),
    path('', include('feeds.urls')),
    path('', include('static.urls')),
    path('', include('unique.urls')),
    path('', include('face_detection.urls')),
    path('', include('jmicc.urls')),
    path('admin/', admin.site.urls),
]
