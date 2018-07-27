#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import template
from django.contrib import messages
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.urls import reverse_lazy

from ..assets import ASSETS
from ..menu import Menu
from ..messages import MessagesList
from ..notifications import NotificationList
from ..tasks import TaskList
from ..utils import Html

register = template.Library()

@register.filter
def hash(h, key):
    return h.get(key,None)

@register.simple_tag
def link_css(url):
    name = '{}_css'.format(url).lower()
    url = Html.static(
        ASSETS.get(name, url)
    )
    return Html.css_file(url)


@register.simple_tag
def link_js(url):
    name = '{}_js'.format(url).lower()
    url = Html.static(
        ASSETS.get(name, url)
    )
    return Html.js_file(url)


@register.simple_tag
def gravatar_url(email, size=200):
    return Html.gravatar_url(email, size)

@register.simple_tag
def avatar_url(user):
    if user.profile.avatar:
        return reverse_lazy("account:avatar")
    else:
        return static("user-circle-o.png")

@register.simple_tag(takes_context=True)
def ui_theme(context,default="skin-blue"):
    user = context.get('request').user
    skin = default
    try:
        skin = user.profile.active.ui_skin
    except:
        pass
    if skin == None:
        skin = default

    return skin


# @register.inclusion_tag('adminlte_full/breadcrumb/breadcrumb.html')
# def show_breadcrumb():
#     return {}


@register.inclusion_tag('dashboard/inc/flash-message.html')
def show_flash_message(message):
    icon = message.level_tag

    if message.level_tag == messages.DEFAULT_TAGS[messages.DEBUG]:
        icon = 'bug'
    elif message.level_tag == messages.DEFAULT_TAGS[messages.ERROR]:
        icon = 'ban'
    elif message.level_tag == messages.DEFAULT_TAGS[messages.SUCCESS]:
        icon = 'check'

    return {
        'message': message,
        'level_class': message.level_tag,
        'icon': 'fa fa-' + icon
    }


@register.inclusion_tag('dashboard/sidebar/menu.html', takes_context=True)
def show_menu(context):
    sender = Menu()
    sender.show_signal.send(sender,context=context)
    sender.activate_by_context(context)

    return {
        'menu': sender.items
    }


@register.inclusion_tag('dashboard/navbar/messages.html')
def show_messages():
    sender = MessagesList()
    result = sender.show_signal.send(sender)

    if len(result):
        return {
            'messages': sender.messages,
            'total': sender.total,
        }


@register.inclusion_tag('dashboard/navbar/notifications.html', takes_context=True)
def show_notifications(context):
    sender = NotificationList()
    result = sender.show_signal.send(sender, context=context)

    if len(result):
        if sender.total > 0:
            return {
                'notifications': sender.notifications,
                'total': sender.total,
            }

@register.inclusion_tag('dashboard/sidebar/search-form.html')
def show_search_form():
    return {}

@register.inclusion_tag('dashboard/navbar/tasks.html', takes_context=True)
def show_tasks(context):
    sender = TaskList()
    result = sender.show_signal.send(sender, context=context)

    if len(result):
        return {
            'tasks': sender.tasks,
            'total': sender.total,
        }


@register.inclusion_tag('dashboard/navbar/user.html', takes_context=True)
def show_user(context):
    return {
        'user': context.get('request').user # ????
    }

# @register.inclusion_tag('adminlte_full/sidebar/user-panel.html')
# def show_user_panel():
#     return {}


@register.inclusion_tag('dashboard/sidebar/user-panel.html', takes_context=True)
def show_user_panel(context):
    return {
        'user': context.get('request').user
    }
