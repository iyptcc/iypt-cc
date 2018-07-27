import html
import os
import platform
import socket
import sys
from collections import Counter

import django
import pipdeptree
import pkg_resources
import psutil
from django.conf import settings
from django.db import connection


def get_virtualenv_packages():
    """
    Return list of installed packages in the virtualenv of application
    """
    return sorted([(i.key, i.version) for i in pkg_resources.working_set])


def get_requirement_packages():
    """
    Return list of requirements packages
    Each package can have some dependences
    """
    packages = []
    fname = settings.BASE_DIR.child("requirements").child("_base.txt")
    with open(fname) as f:
        for line in f:
            packages.append(line.split("\n")[0])
        return packages


def get_virtual_dependencies_of_packages():
    """
    Return information about installed dependencies in the virtualenv of application

    example of json result :

    {"dependencies": [{"required_version": null,
        "installed_version": "1.8.13", "package_name": "Django", "key": "django"}],
    "package_name": "django-ckeditor"}
    """
    packages = pkg_resources.working_set
    dist_index = pipdeptree.build_dist_index(packages)
    tree = pipdeptree.construct_tree(dist_index)

    packages_dict = {}
    locations = []
    for p in packages:
        packages_dict[p.key] = p
        locations.append(p.location)

    most_common = Counter(locations).most_common(1)[0][0]
    print("most common loc")
    print(most_common)

    ret = [{'package_name': k.as_dict()['key'], 'dependencies': [v.as_dict() for v in vs]} for k, vs in tree.items()]
    for r  in ret:
        r["package"] = packages_dict[r["package_name"]]
        r["dependency_for"] = []
        if r["package"].location == most_common:
            r["default_location"] = True
        for rr in ret:
            if r['package'].key in [d['key'] for d in rr["dependencies"]]:
                r["dependency_for"].append(rr["package_name"])

    sortedret = sorted(ret,key=(lambda x: (len(x["dependencies"]) , x["package_name"] ) ))
    return most_common, sortedret

def get_django_version():
    """
    Return the version of Django
    """
    return django.__version__


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
    data += [('OS Version', '%s %s' % (platform.system(), platform.release()) )]
    data += [('Platform', platform.platform())]
    if hasattr(os, 'path'): data += [('OS Path', os.environ['PATH'].split(':'),':')]
    if hasattr(sys, 'version'): data += [('Python Version', ''.join(sys.version))]
    if hasattr(sys, 'subversion'): data += [('Python Subversion', ', '.join(sys.subversion))]
    if hasattr(sys, 'prefix'): data += [('Python Prefix', sys.prefix)]
    if hasattr(sys, 'path'): data += [('Python Path', sys.path,' ')]
    if hasattr(sys, 'executable'): data += [('Python Executable', sys.executable)]
    data += [('Build Date', platform.python_build()[1])]
    data += [('Compiler', platform.python_compiler())]

    if hasattr(sys, 'api_version'): data += [('Python API', sys.api_version)]
    return data

def get_py_internals():
    data = []
    if hasattr( sys, 'builtin_module_names' ):
        data += [('Built-in Modules', sys.builtin_module_names, ',')]
        data += [('Byte Order', sys.byteorder + ' endian')]
    if hasattr( sys, 'getcheckinterval' ): data += [('Check Interval', sys.getcheckinterval())]
    if hasattr(sys, 'getfilesystemencoding'):
        data += [('File System Encoding', sys.getfilesystemencoding())]
        data += [('Maximum Integer Size', str( sys.maxsize ) + ' (%s)' % str( hex( sys.maxsize ) ).upper().replace( "X", "x" ))]
    if hasattr( sys, 'getrecursionlimit' ): data += [('Maximum Recursion Depth', sys.getrecursionlimit())]
    if hasattr( sys, 'tracebacklimit' ): data += [('Maximum Traceback Limit', sys.tracebacklimit)]
    else:
        data += [('Maximum Traceback Limit', '1000')]
        data += [('Maximum Unicode Code Point', sys.maxunicode)]
    return data

def get_os_internals():
    data = []
    if hasattr( os, 'getcwd' ):     data += [('Current Working Directory', os.getcwd())]
    if hasattr( os, 'getegid' ):    data += [('Effective Group ID', os.getegid())]
    if hasattr( os, 'geteuid' ):    data += [('Effective User ID', os.geteuid())]
    if hasattr( os, 'getgid' ):     data += [('Group ID', os.getgid())]
    if hasattr( os, 'getgroups' ):  data += [('Group Membership', map( str, os.getgroups() ),',' )]
    if hasattr( os, 'linesep' ):    data += [('Line Seperator', repr( os.linesep )[1:-1] )]
    if hasattr( os, 'getloadavg' ): data += [('Load Average', map( str, map( lambda x: round( x, 2 ), os.getloadavg() ) ), ', ' )]
    if hasattr( os, 'pathsep' ):    data += [('Path Seperator', os.pathsep)]
    try:
        if hasattr( os, 'getpid' ) and hasattr( os, 'getppid' ):
            data += [('Process ID', ( '%s (parent: %s)' % ( os.getpid(), os.getppid() ) ) )]
    except:
        pass
    if hasattr( os, 'getuid' ): data += [('User ID', os.getuid() )]
    return data

def get_environ():
    envvars = os.environ.keys()
    envvars = sorted( envvars )
    data = []
    for envvar in envvars:
        data += [(envvar, html.escape( str( os.environ[envvar] ) ) )]
    return data

def get_socket():
    data  = []
    data += [('Hostname', socket.gethostname())]
    data += [('Hostname (fully qualified)', socket.gethostbyaddr( socket.gethostname() )[0])]
    try:
        data += [('IP Address', socket.gethostbyname( socket.gethostname() ))]
    except:
        pass
    data += [('IPv6 Support', getattr( socket, 'has_ipv6', False ))]
    try:
        data += [('IPv6 Address', socket.gethostbyaddr( socket.gethostname() )[2],", ")]
    except:
        pass
    data += [('SSL Support', hasattr( socket, 'ssl' ))]
    return data

def to_bi(n):

    ret = n
    exts = ["B","kB","MB","GB"]
    power = 0
    while ret > 1500:
        ret /= 1024
        power += 1

    return "%.2f %s"%(ret,exts[power])

def mem():
    phymem = psutil.virtual_memory()
    total = phymem.total
    #phymem.free + buffers + cached
    free = phymem.available
    used = total - free
    return [("Total",to_bi(total)), ("Used",to_bi(used)), ("Free", to_bi(free))]

def df():
    '''disk_usage'''
    df = []
    for part in psutil.disk_partitions(all=False):
        usage = psutil.disk_usage(part.mountpoint)
        percent = str(int(usage.percent)) + '%'
        disk = [part.device, to_bi(usage.total),
                to_bi(usage.used), to_bi(usage.free),
                percent, part.mountpoint]
        df.append(disk)
    return df

def get_information(request):
    """
    Return information about the application
    """


    information_dict = {}
    #information_dict['service_name'] = settings.APPLICATION_NAME
    information_dict['client_ip'] = request.META['REMOTE_ADDR']
    information_dict['django_version'] = get_django_version()
    #information_dict['db_version'] = get_database_version()
    information_dict['os_version'] = get_system()
    information_dict['python_internals'] = get_py_internals()
    information_dict['os_internals'] = get_os_internals()
    information_dict['memory'] = mem()
    information_dict['disk'] = df()
    information_dict['environment'] = get_environ()
    information_dict['socket'] = get_socket()
    #information_dict['virtualenv_packages'] = get_virtualenv_packages()
    #information_dict['requirement_packages'] = get_requirement_packages()
    common_path, deps = get_virtual_dependencies_of_packages()
    information_dict['virtualenv_dependencies'] = deps
    information_dict['virtualenv_dependencies_path'] = common_path

    return information_dict
