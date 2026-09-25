import logging
import time
import uuid

from django.http import JsonResponse

logger = logging.getLogger("procezo.requests")


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        start = time.monotonic()
        try:
            response = self.get_response(request)
        except Exception as exc:
            logger.error("unhandled_request", extra={"request_id": request.request_id, "exception_type": type(exc).__name__})
            response = JsonResponse({"code": "server_error", "message": "Erreur interne.", "request_id": request.request_id}, status=500)
        response["X-Request-ID"] = request.request_id
        logger.info("request", extra={"request_id": request.request_id, "route": getattr(getattr(request, "resolver_match", None), "route", "unmatched"), "status": response.status_code, "duration_ms": round((time.monotonic() - start) * 1000)})
        return response
