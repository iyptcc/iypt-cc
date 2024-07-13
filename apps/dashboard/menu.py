#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import OrderedDict

import django.dispatch
from django.urls import resolve, reverse


class MenuItem(object):
    COLOR_AQUA = "aqua"
    COLOR_GREEN = "green"
    COLOR_RED = "red"
    COLOR_YELLOW = "yellow"

    def __init__(
        self,
        uid,
        label,
        route,
        route_args=None,
        icon=False,
        badge=False,
        badge_color=None,
        badges=None,
    ):
        self.__active = False
        self.__parent = None
        self.__children = []
        self.__route_args = route_args or {}
        self.__display = False

        self.uid = uid
        self.label = label
        self.route = route
        self.icon = icon
        if badge:
            self.badges = [(badge, badge_color or self.COLOR_GREEN)]
        else:
            self.badges = badges
            if type(badges) == tuple:
                self.badges = [badges]

    @property
    def active(self):
        return self.__active

    @property
    def display(self):
        return self.__display

    @active.setter
    def active(self, active):
        self.__active = bool(active)

        if self.has_parent():
            self.parent.active |= bool(self.parent.has_active_child())

    @display.setter
    def display(self, display):
        self.__display = bool(display)

        if self.has_parent():
            self.parent.display = bool(display)

    def add_child(self, child):
        if isinstance(child, MenuItem):
            child.parent = self
            self.__children.append(child)

    @property
    def children(self):
        return self.__children

    @children.setter
    def children(self, children):
        for child in children:
            self.add_child(child)

    def has_active_child(self):
        for child in self.children:
            if child.is_active():
                return True
        return None

    def has_children(self):
        return bool(self.children)

    def has_parent(self):
        return isinstance(self.parent, MenuItem)

    def is_active(self):
        return bool(self.active)

    def to_display(self):
        return bool(self.display)

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, parent):
        if isinstance(parent, MenuItem):
            self.__parent = parent

    def remove_child(self, child):
        if child in self.children:
            self.children.remove(child)

    @property
    def route_args(self):
        return self.__route_args

    @route_args.setter
    def route_args(self, route_args):
        if isinstance(route_args, dict):
            self.__route_args = route_args

    def url(self):
        if (self.route is not None) and (self.route != "#"):
            return reverse(self.route, kwargs=self.route_args)
        return ""


class Menu(object):
    show_signal = django.dispatch.Signal()

    def __init__(self):
        self.__items = OrderedDict()

    def __activate_by_path(self, path, items):
        for item in items:
            if item.has_children():
                self.__activate_by_path(path, item.children)
            else:
                item.active = self.__path_equals_route(path, item.route)

    def __display_by_session(self, session, items):
        for item in items:
            if item.has_children():
                self.__display_by_session(session, item.children)

            item.display = session.get("menu-display-%d" % item.uid, False)

    def __path_equals_route(self, path, route):
        resolved = False

        try:
            resolved = resolve(path)
        except:
            pass

        if hasattr(resolved, "namespaces"):
            return resolved and resolved.namespace + ":" + resolved.url_name == route
        return resolved and ":".join(resolved.namespaces + [resolved.url_name]) == route

    def activate_by_context(self, context):
        self.__display_by_session(context.get("request").session, self.items.values())
        self.__activate_by_path(context.get("request").path, self.items.values())

    def add_item(self, item):
        if isinstance(item, MenuItem):
            self.__items[item.uid] = item

    @property
    def items(self):
        return OrderedDict(sorted(self.__items.items(), key=lambda x: x[0]))

    @items.setter
    def items(self, items):
        for item in items:
            self.add_item(item)

    def root_item(self, uid):
        return self.items.get(uid)
