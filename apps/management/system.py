import hashlib
import html
import importlib
import os
import platform
import socket
import sys
from itertools import chain
from typing import Any

import django
import psutil
from django.conf import settings
from django.db import connection
from pipdeptree._discovery import get_installed_distributions
from pipdeptree._models import DistPackage, PackageDAG, ReqPackage
from pipdeptree._validate import conflicting_deps


def get_top_level_nodes(tree: PackageDAG, *, list_all: bool) -> list[DistPackage]:
    """
    Get a list of nodes that will appear at the first depth of the dependency tree.

    :param tree: the package tree
    :param list_all: whether to list all the pkgs at the root level or only those that are the sub-dependencies
    """
    tree = tree.sort()
    nodes = list(tree.keys())
    branch_keys = {r.key for r in chain.from_iterable(tree.values())}

    if not list_all:
        nodes = [p for p in nodes if p.key not in branch_keys]

    return nodes


def _render_text_with_unicode(
    tree: PackageDAG,
    nodes: list[DistPackage],
    max_depth: float,
    include_license: bool,  # noqa: FBT001
) -> str:
    def aux(  # noqa: PLR0913, PLR0917
        node: DistPackage | ReqPackage,
        parent: DistPackage | ReqPackage | None = None,
        indent: int = 0,
        cur_chain: list[str] | None = None,
        prefix: str = "",
        depth: int = 0,
        has_grand_parent: bool = False,  # noqa: FBT001, FBT002
        is_last_child: bool = False,  # noqa: FBT001, FBT002
        parent_is_last_child: bool = False,  # noqa: FBT001, FBT002
    ) -> list[Any]:
        cur_chain = cur_chain or []
        node_str = node.render(parent, frozen=False)
        next_prefix = ""
        next_indent = indent + 2

        if parent:
            bullet = "├── "
            if is_last_child:
                bullet = "└── "

            if has_grand_parent:
                next_indent -= 1
                if parent_is_last_child:
                    prefix += " " * (indent + 1 - depth)
                else:
                    prefix += "│" + " " * (indent - depth)
                # Without this extra space, bullets will point to the space just before the project name
                prefix += " "
            next_prefix = prefix
            node_str = prefix + bullet + node_str
        elif include_license:
            node_str += " " + node.licenses()

        result = [node_str]

        children = tree.get_children(node.key)
        children_strings = [
            aux(
                c,
                node,
                indent=next_indent,
                cur_chain=[*cur_chain, c.project_name],
                prefix=next_prefix,
                depth=depth + 1,
                has_grand_parent=parent is not None,
                is_last_child=c is children[-1],
                parent_is_last_child=is_last_child,
            )
            for c in children
            if c.project_name not in cur_chain and depth + 1 <= max_depth
        ]

        result += list(chain.from_iterable(children_strings))
        return result

    lines = chain.from_iterable([aux(p) for p in nodes])
    return "\n".join(lines)  # noqa: T201


def get_virtual_dependencies_of_packages():
    pkgs = get_installed_distributions()

    tree = PackageDAG.from_pkgs(pkgs)

    conflicts = conflicting_deps(tree)

    conf_lines = []
    pkgs = sorted(conflicts.keys())
    for p in pkgs:
        pkg = p.render_as_root(frozen=False)
        conf_lines.append(f"* {pkg}")  # noqa: T201
        for req in conflicts[p]:
            req_str = req.render_as_branch(frozen=False)
            conf_lines.append(f" - {req_str}")  # noqa: T201

    nodes = get_top_level_nodes(tree, list_all=True)

    ret = _render_text_with_unicode(
        tree, nodes, max_depth=float("inf"), include_license=False
    )
    return "\n".join(conf_lines), ret


def get_django_version():
    """
    Return the version of Django
    """
    return django.__version__


def get_glue_release():
    """
    Return the version of GLUE
    """
    release_hash = "unknown"
    try:
        with open(
            os.path.join(os.path.dirname(settings.BASE_DIR), "django-git/HEAD")
        ) as f:
            release_hash = f.read()
    except IOError:
        pass
    return release_hash


def get_python_version():
    """
    Return the version of python
    """
    return ".".join(map(str, sys.version_info[:3]))


def get_database_version():
    """
    Return the version of database
    """
    cursor = connection.cursor()
    cursor.execute("SELECT VERSION();")
    row = cursor.fetchone()
    return row[0]


def get_system():
    """
    Return the version of OS
    """
    data = []
    data += [("OS Version", "%s %s" % (platform.system(), platform.release()))]
    data += [("Platform", platform.platform())]
    if hasattr(os, "path"):
        data += [("OS Path", os.environ["PATH"].split(":"), ":")]
    if hasattr(sys, "version"):
        data += [("Python Version", "".join(sys.version))]
    if hasattr(sys, "subversion"):
        data += [("Python Subversion", ", ".join(sys.subversion))]
    if hasattr(sys, "prefix"):
        data += [("Python Prefix", sys.prefix)]
    if hasattr(sys, "path"):
        data += [("Python Path", sys.path, " ")]
    if hasattr(sys, "executable"):
        data += [("Python Executable", sys.executable)]
    data += [("Build Date", platform.python_build()[1])]
    data += [("Compiler", platform.python_compiler())]

    if hasattr(sys, "api_version"):
        data += [("Python API", sys.api_version)]
    return data


def get_py_internals():
    data = []
    if hasattr(sys, "builtin_module_names"):
        data += [("Built-in Modules", sys.builtin_module_names, ",")]
        data += [("Byte Order", sys.byteorder + " endian")]
    if hasattr(sys, "getcheckinterval"):
        data += [("Check Interval", sys.getcheckinterval())]
    if hasattr(sys, "getfilesystemencoding"):
        data += [("File System Encoding", sys.getfilesystemencoding())]
        data += [
            (
                "Maximum Integer Size",
                str(sys.maxsize)
                + " (%s)" % str(hex(sys.maxsize)).upper().replace("X", "x"),
            )
        ]
    if hasattr(sys, "getrecursionlimit"):
        data += [("Maximum Recursion Depth", sys.getrecursionlimit())]
    if hasattr(sys, "tracebacklimit"):
        data += [("Maximum Traceback Limit", sys.tracebacklimit)]
    else:
        data += [("Maximum Traceback Limit", "1000")]
        data += [("Maximum Unicode Code Point", sys.maxunicode)]
    return data


def get_os_internals():
    data = []
    if hasattr(os, "getcwd"):
        data += [("Current Working Directory", os.getcwd())]
    if hasattr(os, "getegid"):
        data += [("Effective Group ID", os.getegid())]
    if hasattr(os, "geteuid"):
        data += [("Effective User ID", os.geteuid())]
    if hasattr(os, "getgid"):
        data += [("Group ID", os.getgid())]
    if hasattr(os, "getgroups"):
        data += [("Group Membership", map(str, os.getgroups()), ",")]
    if hasattr(os, "linesep"):
        data += [("Line Seperator", repr(os.linesep)[1:-1])]
    if hasattr(os, "getloadavg"):
        data += [
            (
                "Load Average",
                map(str, map(lambda x: round(x, 2), os.getloadavg())),
                ", ",
            )
        ]
    if hasattr(os, "pathsep"):
        data += [("Path Seperator", os.pathsep)]
    try:
        if hasattr(os, "getpid") and hasattr(os, "getppid"):
            data += [("Process ID", ("%s (parent: %s)" % (os.getpid(), os.getppid())))]
    except:
        pass
    if hasattr(os, "getuid"):
        data += [("User ID", os.getuid())]
    return data


def get_environ():
    envvars = os.environ.keys()
    envvars = sorted(envvars)
    data = []
    censor_end = ["_PASS", "_PASSWORD", "_KEY"]
    for envvar in envvars:
        if any([envvar.endswith(e) for e in censor_end]):
            data += [(envvar, html.escape("****sensitive***"))]
        else:
            data += [(envvar, html.escape(str(os.environ[envvar])))]
    return data


def get_socket():
    data = []
    data += [("Hostname", socket.gethostname())]
    data += [
        ("Hostname (fully qualified)", socket.gethostbyaddr(socket.gethostname())[0])
    ]
    try:
        data += [("IP Address", socket.gethostbyname(socket.gethostname()))]
    except:
        pass
    data += [("IPv6 Support", getattr(socket, "has_ipv6", False))]
    try:
        data += [("IPv6 Address", socket.gethostbyaddr(socket.gethostname())[2], ", ")]
    except:
        pass
    data += [("SSL Support", hasattr(socket, "ssl"))]
    return data


def to_bi(n):

    ret = n
    exts = ["B", "kB", "MB", "GB", "TB"]
    power = 0
    while ret > 1500:
        ret /= 1024
        power += 1

    return "%.2f %s" % (ret, exts[power])


def mem():
    phymem = psutil.virtual_memory()
    total = phymem.total
    # phymem.free + buffers + cached
    free = phymem.available
    used = total - free
    return [("Total", to_bi(total)), ("Used", to_bi(used)), ("Free", to_bi(free))]


def sec():

    # settings.SECRET_KEY
    hash_object = hashlib.sha256(settings.SECRET_KEY.encode("ascii"))
    hex_dig = hash_object.hexdigest()[:20].upper()

    return [
        (
            "Secret digest",
            ":".join([hex_dig[i : i + 2] for i in range(0, len(hex_dig), 2)]),
        )
    ]


def df():
    """disk_usage"""
    df = []
    for part in psutil.disk_partitions(all=False):
        usage = psutil.disk_usage(part.mountpoint)
        percent = str(int(usage.percent)) + "%"
        disk = [
            part.device,
            to_bi(usage.total),
            to_bi(usage.used),
            to_bi(usage.free),
            percent,
            part.mountpoint,
        ]
        df.append(disk)
    return df


def get_information(request):
    """
    Return information about the application
    """

    information_dict = {}
    # information_dict['service_name'] = settings.APPLICATION_NAME
    information_dict["glue_release"] = get_glue_release()
    information_dict["client_ip"] = request.META["REMOTE_ADDR"]
    information_dict["django_version"] = get_django_version()
    # information_dict['db_version'] = get_database_version()
    information_dict["os_version"] = get_system()
    information_dict["python_internals"] = get_py_internals()
    information_dict["os_internals"] = get_os_internals()
    information_dict["memory"] = mem()
    information_dict["security"] = sec()
    information_dict["disk"] = df()
    information_dict["environment"] = get_environ()
    information_dict["socket"] = get_socket()
    conf, deps = get_virtual_dependencies_of_packages()
    information_dict["virtualenv_dependencies_conflicts"] = conf
    information_dict["virtualenv_dependencies"] = deps

    return information_dict
