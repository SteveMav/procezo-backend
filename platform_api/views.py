from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework import serializers
from drf_spectacular.utils import extend_schema


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)


class SessionResponseSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()


@method_decorator(csrf_protect, name="dispatch")
class SessionView(GenericAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = LoginSerializer

    @extend_schema(responses=SessionResponseSerializer)
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"authenticated": request.user.is_authenticated})

    @extend_schema(request=LoginSerializer, responses=SessionResponseSerializer)
    def post(self, request):
        data = LoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = authenticate(request, **data.validated_data)
        if user is None:
            return Response({"code": "authentication_failed", "message": "Identifiants invalides.", "request_id": request.request_id}, status=401)
        login(request, user)
        return Response({"authenticated": True})

    def delete(self, request):
        logout(request)
        return Response(status=204)
