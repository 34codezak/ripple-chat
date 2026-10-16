from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.home, name="home"),
    path("welcome/", views.landing, name="landing"),
    path("chats/list/", views.chat_list, name="list"),
    path("chats/new/", views.new_chat, name="new_chat"),
    path("groups/new/", views.new_group, name="new_group"),
    path("contacts/add/", views.add_contact, name="add_contact"),
    path("settings/", views.settings_view, name="settings"),
    path("notifications/bell/", views.bell, name="bell"),
    path("rooms/<slug:slug>/", views.room, name="room"),
    path("rooms/<slug:slug>/history/", views.history, name="history"),
    path("rooms/<slug:slug>/send/", views.post_message, name="post_message"),
    path("rooms/<slug:slug>/presence/", views.presence, name="presence"),
]
