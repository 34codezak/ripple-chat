"""Shared helpers so HTTP views and the WebSocket consumer behave identically."""
import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db.models import Count, F, IntegerField, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

from .models import ChatRoom, Membership, Message

User = get_user_model()
MAX_MESSAGE_LENGTH = 2000


# --- realtime ---------------------------------------------------------------
def room_group_name(slug: str) -> str:
    return f"chat_{slug}"


def render_message(message) -> str:
    return render_to_string("chat/_message.html", {"message": message})


def broadcast_message(message) -> None:
    async_to_sync(get_channel_layer().group_send)(
        room_group_name(message.room.slug),
        {"type": "chat.message", "html": render_message(message)},
    )


# --- rooms ------------------------------------------------------------------
def get_or_create_direct(a, b):
    lo, hi = sorted([a.pk, b.pk])
    room, _ = ChatRoom.objects.get_or_create(
        slug=f"dm-{lo}-{hi}", defaults={"kind": ChatRoom.DIRECT, "created_by": a}
    )
    for u in (a, b):
        Membership.objects.get_or_create(room=room, user=u)
    return room


def create_group(creator, name, members):
    base = slugify(name)[:60] or "group"
    room = ChatRoom.objects.create(
        name=name, slug=f"{base}-{uuid.uuid4().hex[:6]}", kind=ChatRoom.GROUP, created_by=creator
    )
    Membership.objects.bulk_create([Membership(room=room, user=u) for u in {creator, *members}])
    return room


# --- avatars / presence -------------------------------------------------------
def avatar_url(user):
    profile = getattr(user, "profile", None)  # missing profile raises an AttributeError subclass
    return profile.avatar.url if profile and profile.avatar else ""


def room_header(room, user):
    others = list(User.objects.filter(memberships__room=room).exclude(pk=user.pk).select_related("profile"))
    active = sum(1 for u in others if getattr(u, "profile", None) and u.profile.connections > 0)
    if room.kind == ChatRoom.DIRECT and others:
        other = others[0]
        profile = getattr(other, "profile", None)
        return {
            "title": other.username,
            "subtitle": profile.about if profile else "",
            "avatar_url": avatar_url(other),
            "active": active > 0,
            "label": "Active" if active else "Inactive",
        }
    return {
        "title": room.name,
        "subtitle": f"{len(others) + 1} members",
        "avatar_url": "",
        "active": active > 0,
        "label": f"{active} active" if active else "Inactive",
    }


# --- unread / chat list -------------------------------------------------------
def unread_total(user) -> int:
    return (
        Message.objects.filter(
            room__memberships__user=user, timestamp__gt=F("room__memberships__last_read_at")
        )
        .exclude(user=user)
        .count()
    )


def _time_label(dt):
    if not dt:
        return ""
    local = timezone.localtime(dt)
    if local.date() == timezone.localdate():
        return local.strftime("%H:%M")
    return local.strftime("%d %b")


def chat_rows(user, q="", kind=None):
    last = Message.objects.filter(room=OuterRef("room")).order_by("-timestamp")
    unread = (
        Message.objects.filter(room=OuterRef("room"), timestamp__gt=OuterRef("last_read_at"))
        .exclude(user=OuterRef("user"))
        .order_by()
        .values("room")
        .annotate(c=Count("pk"))
        .values("c")
    )
    qs = (
        Membership.objects.filter(user=user)
        .select_related("room")
        .annotate(
            unread=Coalesce(Subquery(unread, output_field=IntegerField()), Value(0)),
            last_text=Subquery(last.values("content")[:1]),
            last_time=Subquery(last.values("timestamp")[:1]),
            last_sender=Subquery(last.values("user__username")[:1]),
        )
        .order_by(F("last_time").desc(nulls_last=True), "-joined_at")
    )
    if kind:
        qs = qs.filter(room__kind=kind)
    rows = list(qs)

    dm_ids = [r.room_id for r in rows if r.room.kind == ChatRoom.DIRECT]
    others = {
        m.room_id: m.user
        for m in Membership.objects.filter(room_id__in=dm_ids).exclude(user=user).select_related("user__profile")
    }
    for r in rows:
        other = others.get(r.room_id)
        r.title = other.username if other else (r.room.name or r.room.slug)
        r.avatar_url = avatar_url(other) if other else ""
        r.time_label = _time_label(r.last_time)
    if q:
        rows = [r for r in rows if q in r.title.lower()]
    return rows
