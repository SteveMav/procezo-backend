from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from platform_api.views import SessionView
from audit.views import AuditListView
from cases.views import CaseViewSet
from intelligence.views import IntelligenceViewSet, DisseminationViewSet
from documents.views import DocumentViewSet
from requests_app.views import RequestViewSet, ActViewSet, ResponseViewSet
from inspections.views import MissionViewSet, SheetViewSet, SheetProjectViewSet, DefenseViewSet
from cases.work import WorkListView, ToValidateView
from decisions.views import DecisionViewSet, GelecTransferViewSet
from reporting.views import StatisticsView, StatisticsDetailView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("dossiers", CaseViewSet, basename="dossier")
router.register("renseignements", IntelligenceViewSet, basename="renseignement")
router.register("diffusions", DisseminationViewSet, basename="diffusion")
router.register("documents", DocumentViewSet, basename="document")
router.register("demandes", RequestViewSet, basename="demande")
router.register("actes", ActViewSet, basename="acte")
router.register("reponses", ResponseViewSet, basename="reponse")
router.register("missions", MissionViewSet, basename="mission")
router.register("feuilles", SheetViewSet, basename="feuille")
router.register("projets-feuille", SheetProjectViewSet, basename="projet-feuille")
router.register("defenses", DefenseViewSet, basename="defense")
router.register("decisions", DecisionViewSet, basename="decision")
router.register("transferts-gelec", GelecTransferViewSet, basename="transfert-gelec")

urlpatterns = [
    path("api/v1/session/", SessionView.as_view(), name="session"),
    path("api/v1/audit/", AuditListView.as_view(), name="audit-list"),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/mon-travail/", WorkListView.as_view(), name="mon-travail"),
    path("api/v1/a-valider/", ToValidateView.as_view(), name="a-valider"),
    path("api/v1/statistiques/", StatisticsView.as_view(), name="statistics"),
    path("api/v1/statistiques/<str:key>/", StatisticsDetailView.as_view(), name="statistics-detail"),
    path("api/v1/", include(router.urls)),
]

handler403 = "platform_api.errors.forbidden"
handler404 = "platform_api.errors.not_found"
handler500 = "platform_api.errors.server_error"
