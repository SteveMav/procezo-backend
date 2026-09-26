import logging

from django.db import OperationalError
from django.http import Http404
from django.http import JsonResponse
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


logger = logging.getLogger("procezo.requests")


class Conflict(APIException):
    status_code = 409
    default_code = "conflict"
    default_detail = "La version de la ressource a changé. Rechargez-la."


class DependencyUnavailable(APIException):
    status_code = 503
    default_code = "dependency_unavailable"
    default_detail = "Service temporairement indisponible."


def exception_handler(exc, context):
    request = context.get("request")
    request_id = getattr(request, "request_id", "")
    if isinstance(exc, OperationalError):
        logger.error("database_locked" if "locked" in str(exc).lower() else "database_unavailable", extra={"request_id": request_id})
        exc = DependencyUnavailable()
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    code = exc.get_codes() if hasattr(exc, "get_codes") else "not_found" if isinstance(exc, Http404) else "error"
    if isinstance(code, (dict, list)):
        code = "validation_error"
    safe_messages = {
        "not_authenticated": "Authentification requise.",
        "authentication_failed": "Identifiants invalides.",
        "permission_denied": "Action interdite.",
        "not_found": "Ressource introuvable.",
        "conflict": "La version de la ressource a changé. Rechargez-la.",
        "dependency_unavailable": "Service temporairement indisponible.",
        "validation_error": "Entrée invalide.",
        "parse_error": "Entrée invalide.",
    }
    response.data = {"code": str(code), "message": safe_messages.get(str(code), "Requête invalide."), "request_id": request_id}
    if response.status_code == 400 and isinstance(getattr(exc, "detail", None), dict):
        response.data["fields"] = {key: [str(item) for item in value] if isinstance(value, list) else [str(value)] for key, value in exc.detail.items()}
    return response


def server_error(request):
    return JsonResponse({"code": "server_error", "message": "Erreur interne.", "request_id": getattr(request, "request_id", "")}, status=500)


def not_found(request, exception):
    return JsonResponse({"code": "not_found", "message": "Ressource introuvable.", "request_id": getattr(request, "request_id", "")}, status=404)


def forbidden(request, exception):
    return JsonResponse({"code": "permission_denied", "message": "Action interdite.", "request_id": getattr(request, "request_id", "")}, status=403)
