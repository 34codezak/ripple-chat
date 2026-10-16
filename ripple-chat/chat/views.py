from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ProfileForm
from .models import ChatRoom, Contact, Membership, Message, Profile
from .services import (
    MAX_MESSAGE_LENGTH,
    avatar_url,
    broadcast_message,
    chat_rows,
    create_group,
    get_or_create_direct,
    room_header,
)

User = get_user_model()
HISTORY_LIMIT = 50

SLIDES = [
    {"img": "illustrations/slide-1.svg", "caption": "Talk with your people, in groups or one to one."},
    {"img": "illustrations/slide-2.svg", "caption": "Every message sends ripples across the water."},
    {"img": "illustrations/slide-3.svg", "caption": "Calm waters or a storm: Ripple keeps you connected."},
]


def _membership_or_404(user, slug):
    return get_object_or_404(Membership.objects.select_related("room"), user=user, room__slug=slug)


def _contacts(user):
    return User.objects.filter(added_by__owner=user).order_by("username")


# --- public -------------------------------------------------------------------
def landing(request):
    return render(request, "chat/landing.html", {"slides": SLIDES})


def home(request):
    if not request.user.is_authenticated:
        return landing(request)
    return render(request, "chat/home.html", {"rows": chat_rows(request.user)})


def signup(request):
    if request.user.is_authenticated:
        return redirect("chat:home")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("chat:home")
    return render(request, "registration/signup.html", {"form": form})


# --- chat list / header partials ------------------------------------------------
@login_required
def chat_list(request):
    q = request.GET.get("q", "").strip().lower()
    kind = ChatRoom.GROUP if request.GET.get("tab") == "groups" else None
    return render(request, "chat/_chat_list.html", {"rows": chat_rows(request.user, q, kind)})


@login_required
def bell(request):
    return render(request, "chat/_bell_badge.html")


# --- starting chats ---------------------------------------------------------------
@login_required
def new_chat(request):
    contacts = _contacts(request.user)
    if request.method == "POST":
        target = get_object_or_404(contacts, pk=request.POST.get("user_id"))
        return redirect("chat:room", slug=get_or_create_direct(request.user, target).slug)
    return render(request, "chat/new_chat.html", {"contacts": contacts})


@login_required
def new_group(request):
    contacts = _contacts(request.user)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()[:80]
        members = contacts.filter(pk__in=request.POST.getlist("members"))
        if not name:
            messages.error(request, "Give the group a name.")
        elif not members:
            messages.error(request, "Pick at least one contact.")
        else:
            return redirect("chat:room", slug=create_group(request.user, name, members).slug)
    return render(request, "chat/new_group.html", {"contacts": contacts})


@login_required
def add_contact(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip().lstrip("@")
        target = User.objects.filter(username__iexact=username).first()
        if not target:
            messages.error(request, f"No Ripple user called “{username}”.")
        elif target == request.user:
            messages.error(request, "That's you!")
        else:
            _, created = Contact.objects.get_or_create(owner=request.user, contact=target)
            messages.success(request, f"{target.username} {'added' if created else 'is already in your contacts'}.")
        return redirect("chat:add_contact")
    return render(request, "chat/add_contact.html", {"contacts": _contacts(request.user)})


@login_required
def settings_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("chat:settings")
    return render(request, "chat/settings.html", {"form": form, "profile": profile})


# --- a conversation ---------------------------------------------------------------
@login_required
def room(request, slug):
    membership = _membership_or_404(request.user, slug)
    Membership.objects.filter(pk=membership.pk).update(last_read_at=timezone.now())
    ctx = {"room": membership.room, **room_header(membership.room, request.user)}
    return render(request, "chat/chat_room.html", ctx)


@login_required
def presence(request, slug):
    membership = _membership_or_404(request.user, slug)
    ctx = {"room": membership.room, **room_header(membership.room, request.user)}
    return render(request, "chat/_presence.html", ctx)


@login_required
def history(request, slug):
    room = _membership_or_404(request.user, slug).room
    latest = Message.objects.filter(room=room).select_related("user").order_by("-timestamp")[:HISTORY_LIMIT]
    return render(request, "chat/_message_list.html", {"messages": reversed(list(latest))})


@login_required
@require_POST
def post_message(request, slug):
    """Save to DB, broadcast to the room group, return 204 (the socket delivers it to everyone)."""
    room = _membership_or_404(request.user, slug).room
    content = request.POST.get("content", "").strip()[:MAX_MESSAGE_LENGTH]
    if content:
        broadcast_message(Message.objects.create(room=room, user=request.user, content=content))
    return HttpResponse(status=204)


# --- PWA --------------------------------------------------------------------------
def service_worker(request):
    response = render(request, "sw.js", {"cache_version": settings.SW_CACHE_VERSION}, content_type="application/javascript")
    response["Cache-Control"] = "no-cache"
    response["Service-Worker-Allowed"] = "/"
    return response


def offline(request):
    return render(request, "offline.html")
