from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from chat.models import ChatRoom, Membership, Profile


class Command(BaseCommand):
    help = "Create missing profiles and add every user to rooms that have no members (Milestone 1 rooms)."

    def handle(self, *args, **options):
        User = get_user_model()
        users = list(User.objects.all())
        for u in users:
            Profile.objects.get_or_create(user=u)
        for room in ChatRoom.objects.filter(memberships__isnull=True):
            Membership.objects.bulk_create([Membership(room=room, user=u) for u in users])
            self.stdout.write(f"Added {len(users)} users to '{room}'")
        self.stdout.write(self.style.SUCCESS("Done."))
