from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from chat import views as chat_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # Service worker MUST be served from the site root to control "/" scope.
    path("sw.js", chat_views.service_worker, name="service_worker"),
    path("offline/", chat_views.offline, name="offline"),
    path("accounts/signup/", chat_views.signup, name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("chat.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # dev only (no-op when DEBUG=False)
