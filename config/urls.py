"""URL configuration for config project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("pas/", include("pas.urls")),
    path("pembayaran/", include("pembayaran.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("audit/", include("audit.urls")),
    path("notifikasi/", include("notifikasi.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
