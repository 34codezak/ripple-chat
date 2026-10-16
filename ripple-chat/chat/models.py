from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    about = models.CharField(max_length=140, blank=True, default="Hey there! I'm using Ripple.")
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    # Presence: number of open chat sockets. > 0 means "Active".
    connections = models.PositiveIntegerField(default=0)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Profile<{self.user}>"


class Contact(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="contacts")
    contact = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="added_by")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "contact"], name="unique_contact")]

    def __str__(self):
        return f"{self.owner} -> {self.contact}"


class ChatRoom(models.Model):
    GROUP, DIRECT = "group", "direct"
    KIND_CHOICES = [(GROUP, "Group"), (DIRECT, "Direct")]

    name = models.CharField(max_length=80, blank=True)
    slug = models.SlugField(max_length=80, unique=True)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=GROUP)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_rooms"
    )
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Membership", related_name="rooms")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name or self.slug


class Membership(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    joined_at = models.DateTimeField(default=timezone.now)
    # Everything after this timestamp (from other people) counts as unread.
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["room", "user"], name="unique_membership")]

    def __str__(self):
        return f"{self.user} in {self.room}"


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    content = models.TextField(max_length=2000)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.user}: {self.content[:30]}"
