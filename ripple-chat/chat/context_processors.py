from django.urls import reverse

from .services import unread_total


def ripple(request):
    ctx = {"invite_url": request.build_absolute_uri(reverse("chat:landing"))}
    if request.user.is_authenticated:
        # Callable => only evaluated if a template actually uses it.
        ctx["unread_total"] = lambda: unread_total(request.user)
    return ctx
