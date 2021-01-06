from django.views import View
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from api.models import UserSession
from api.utils.common import token_expires_delta, create_auth_token,\
        to_bytes, get_now

def authenticated(f):
    def check(self, request, *args, **kwargs):
        token = request.headers.get('x-auth-observatory', None)

        if not token:
            return HttpResponseBadRequest("No token in request!")

        try:
            UserSession.objects.get(token=to_bytes(token), expires__gte=get_now())
        except ObjectDoesNotExist:
            return HttpResponseBadRequest("Expired session. Renew token!")
        return f(self, request, *args, **kwargs)
    return check

class LoginView(View):
    def post(self, request):
        username = request.POST.get('username', None)
        password = request.POST.get('password', None)

        if not username or not password:
            return HttpResponseBadRequest("Username and password are required!")

        user = authenticate(username=username, password=password)

        if not user:
            try:
                User.objects.get(username=username)
                msg = "Invalid password."
            except ObjectDoesNotExist:
                msg = "User does not exist."
            return HttpResponseBadRequest(msg)

        # get existing token or remove old one
        try:
            session = UserSession.objects.get(user_id=user.id, expires__gte=get_now())
        except ObjectDoesNotExist:
            date_to = get_now() + token_expires_delta()
            token = create_auth_token()
            session = UserSession.objects.create(user_id=user, token=token, expires=date_to)
            session.save()

        return JsonResponse({'token': str(session.token)})

class LogoutView(View):
    @authenticated
    def post(self, request):
        token = to_bytes(request.headers.get('x-auth-observatory', None))
        session = UserSession.objects.get(token=token)
        session.expires = get_now()
        session.save()
        return HttpResponse()
