from django.http import JsonResponse


def csrf_failure(request, reason=""):
    return JsonResponse({"code": "csrf_failed", "message": "Jeton CSRF invalide ou manquant.", "request_id": getattr(request, "request_id", "")}, status=403)
