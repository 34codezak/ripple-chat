from django.contrib import admin

from .models import ChatRoom, Contact, Membership, Message, Profile


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "kind")
    inlines = [MembershipInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("room", "user", "timestamp")
    list_filter = ("room",)


admin.site.register(Profile)
admin.site.register(Contact)
