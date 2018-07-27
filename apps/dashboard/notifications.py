#!/usr/bin/env python
# -*- coding: utf-8 -*-

import django.dispatch
from django.contrib.messages import get_messages


class NotificationItem(object):
    TYPE_ERROR = 'red'
    TYPE_INFO = 'aqua'
    TYPE_SUCCESS = 'green'
    TYPE_WARNING = 'yellow'

    def __init__(self, message=None, icon=None, tp=None, uid=None):
        self.__uid = uid
        self.icon = icon
        self.message = message
        self.type = tp or self.TYPE_INFO

    @property
    def uid(self):
        return self.__uid


class NotificationList(object):
    show_signal = django.dispatch.Signal()

    def __init__(self):
        self.__notifications = []

    def add_notification(self, notification):
        if isinstance(notification, NotificationItem):
            self.__notifications.append(notification)

    @property
    def notifications(self):
        return self.__notifications

    @notifications.setter
    def notifications(self, notifications):
        for note in notifications:
            self.add_notification(note)

    @property
    def total(self):
        return len(self.notifications)


def user_messages(sender, **kwargs):
    # sender is an instance of Menu class

    request=kwargs['context']['request']
    if request.user.is_authenticated:

        storage = get_messages(request)
        for message in storage:
            n=NotificationItem(message=message.message, tp=message.level)
            sender.add_notification(n)

NotificationList.show_signal.connect(user_messages)
