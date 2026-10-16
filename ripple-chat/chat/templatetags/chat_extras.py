from django import template

register = template.Library()

PALETTE = ["#7a2e22", "#5b2a8c", "#9c4234", "#7c4dbb", "#6b2f45", "#4a3a8f", "#a0522d", "#8e44ad"]


@register.filter
def avatar_color(label):
    return PALETTE[sum(ord(c) for c in str(label or "?")) % len(PALETTE)]


@register.filter
def initials(label):
    parts = str(label or "?").replace("_", " ").replace("-", " ").split()
    return "".join(p[0] for p in parts[:2]).upper() or "?"


@register.filter
def avatar_src(user):
    """Safe avatar URL ('' when the user has no uploaded picture)."""
    from chat.services import avatar_url
    return avatar_url(user)
