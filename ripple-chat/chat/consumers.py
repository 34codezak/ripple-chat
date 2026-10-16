import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import F
from django.utils import timezone

from .models import ChatRoom, Membership, Message, Profile
from .services import MAX_MESSAGE_LENGTH, render_message, room_group_name


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close(code=4401)
            return

        slug = self.scope["url_route"]["kwargs"]["room_name"]
        self.room = await self.get_room(slug)  # None unless the user is a member
        if self.room is None:
            await self.close(code=4404)
            return

        self.group_name = room_group_name(self.room.slug)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.bump_presence(+1)
        self.counted = True

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if getattr(self, "counted", False):
            await self.bump_presence(-1)

    async def receive(self, text_data=None, bytes_data=None):
        """Optional WS-originated send path ({"message": "..."}); the UI posts via HTMX."""
        try:
            content = (json.loads(text_data or "{}").get("message") or "").strip()
        except (ValueError, AttributeError):
            return
        content = content[:MAX_MESSAGE_LENGTH]
        if not content:
            return
        html = await self.save_message(content)
        await self.channel_layer.group_send(self.group_name, {"type": "chat.message", "html": html})

    async def chat_message(self, event):
        # This socket means the room is open on screen, so the message counts as read.
        await self.mark_read()
        await self.send(text_data=json.dumps({"html": event["html"]}))

    # --- DB helpers ---------------------------------------------------------
    @database_sync_to_async
    def get_room(self, slug):
        return ChatRoom.objects.filter(slug=slug, memberships__user=self.user).first()

    @database_sync_to_async
    def save_message(self, content):
        message = Message.objects.create(room=self.room, user=self.user, content=content)
        return render_message(message)

    @database_sync_to_async
    def mark_read(self):
        Membership.objects.filter(room=self.room, user=self.user).update(last_read_at=timezone.now())

    @database_sync_to_async
    def bump_presence(self, delta):
        Profile.objects.get_or_create(user=self.user)
        qs = Profile.objects.filter(user=self.user)
        if delta > 0:
            qs.update(connections=F("connections") + 1, last_seen=timezone.now())
        else:
            qs.filter(connections__gt=0).update(connections=F("connections") - 1, last_seen=timezone.now())
