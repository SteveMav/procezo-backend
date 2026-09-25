from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from platform_api.views import SessionView
from audit.views import AuditListView
from cases.views import CaseViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("dossiers", CaseViewSet, basename="dossier")

urlpatterns = [
    path("api/v1/session/", SessionView.as_view(), name="session"),
    path("api/v1/audit/", AuditListView.as_view(), name="audit-list"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/", include(router.urls)),
]

handler403 = "platform_api.errors.forbidden"
handler404 = "platform_api.errors.not_found"
handler500 = "platform_api.errors.server_error"
