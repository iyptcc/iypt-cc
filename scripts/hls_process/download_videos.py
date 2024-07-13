# Thanks to Simeon

import re
import os
import unicodedata
import time
import urllib
import datetime
import subprocess
import requests
import xml.etree.ElementTree as ET
import dateutil.parser
import hashlib

from .secrets import *

webdav_path = '/public.php/webdav/'
download_prefix = 'src/'

request_headers = {
    'X-Requested-With': 'XMLHttpRequest',
}

def url_until_fqdn(url):
    if not url.startswith('https://') and not url.startswith('http://'):
        raise ValueError('url "%s" does not start with https:// nor with http://'%(str(url)))
    return '/'.join(url.split('/')[0:3])

def share_id_from_url(url):
    parts = url.split('/')
    if parts[-2] != "s":
        raise ValueError('share url "%s" does not contain /s/ before the share ID'%(str(url)))
    return parts[-1]

def filename_from_webdavpath(path, filename_prefix=''):
    return filename_prefix+path.split('/')[-1]

def get_filelist_from_share(url, suffix=''):
    response = requests.request('PROPFIND', url_until_fqdn(url)+webdav_path+suffix,
        headers=request_headers, auth=(share_id_from_url(url), ''))
    if response.status_code != 207:
        raise PermissionError('requests returned status code %d instead of 207'%(response.status_code))

    root = ET.fromstring(response.text)
    if root.tag != "{DAV:}multistatus":
        raise ValueError("response XML doesn't start with a multistatus at top level")

    filelist = []
    for response_child in root:
        webdavpath = response_child.find('{DAV:}href').text
        if webdavpath == webdav_path+suffix:
            continue # skip processind of {DAV:}response describing the folder itself we requested
        filesize = None
        for propstat in response_child:
            if (propstat.find('{DAV:}prop') is not None
                and propstat.find('{DAV:}prop').find('{DAV:}getlastmodified') is not None
                and propstat.find('{DAV:}prop').find('{DAV:}getcontentlength') is not None):
                filesize = int(propstat.find('{DAV:}prop').find('{DAV:}getcontentlength').text)
                modTime = dateutil.parser.parse(propstat.find('{DAV:}prop').find('{DAV:}getlastmodified').text)
                break
            elif (propstat.find('{DAV:}prop') is not None
                and propstat.find('{DAV:}prop').find('{DAV:}resourcetype') is not None
                and propstat.find('{DAV:}prop').find('{DAV:}resourcetype').find('{DAV:}collection') is not None):
                print('descending into %s'%(webdavpath.split('/')[-2]+'/',))
                print("querying: ", url, webdavpath)
                suff=webdavpath[len(webdav_path):]
                print(suff)
                #print("base", os.path.join(os.path.split(webdavpath)[:-1]))
                subfolder_filelist = get_filelist_from_share(url, suffix=suff)
                for subfolder_file in subfolder_filelist:
                    filelist.append(subfolder_file)
                break
        if filesize is not None:
            filelist.append((filename_from_webdavpath(webdavpath, filename_prefix=suffix), filesize, modTime))

    return filelist

def secure_filename_from_webdav_filename(webdav_filename):
    value = str(urllib.parse.unquote(webdav_filename))
    country = value.split('/')[0]
    value = '/'.join(value.split('/')[1:])
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s.-]', '', value.lower())
    return (country,re.sub(r'[-\s]+', '_', value).strip('-_'))

def download_webdavfile_from_share(webdav_filename, url, modificationTime=None):
    country, secure_filename = secure_filename_from_webdav_filename(webdav_filename)
    destinationname = os.path.join(download_prefix,country,secure_filename)
    os.makedirs(os.path.join(download_prefix,country), exist_ok=True)

    if modificationTime is not None:
        if os.path.exists(destinationname):
            statbuf = os.stat(destinationname)
            print(statbuf.st_mtime, 'vs', modificationTime)
            if statbuf.st_mtime == modificationTime: # modification time == modificationTime:
                #skip downloading and processing
                return destinationname

    print("curl commands:", share_id_from_url(url)+':',
        url_until_fqdn(url)+webdav_path+webdav_filename)

    #return destinationname

    print('downloading to %s'%(destinationname))
    subprocess.call(['curl', '--output', destinationname,
        '-H', 'X-Requested-With: XMLHttpRequest', '-u', share_id_from_url(url)+':',
        url_until_fqdn(url)+webdav_path+webdav_filename])

    print("setting modification timestamp of %s to %f"%(destinationname, modificationTime))
    os.utime(destinationname, (modTime.timestamp(), modTime.timestamp()))
    return destinationname


sorted_filelist = sorted(get_filelist_from_share(src_share_url), key=lambda tup: tup[1])
print(sorted_filelist)

for webdav_filename, filesize, modTime in sorted_filelist:
    if not any([webdav_filename.endswith(ext) for ext in [".mp4",".mov",".flv"]]):
        print("not processing non-video:", webdav_filename)
        continue
    print("processing: ", webdav_filename)
    destfile = download_webdavfile_from_share(webdav_filename, src_share_url, modTime.timestamp())

    print(destfile)
    video = os.path.split(destfile)
    team = os.path.split(video[0])[-1]
    videoname = video[-1].split(".")[-2]
    auth = hashlib.blake2b(videoname.encode(), key=authkey, digest_size=16).hexdigest()
    vid = auth + "_" + videoname
    print(team, vid)

    continue
    subprocess.call(
        ['curl', '-H', 'X-Requested-With: XMLHttpRequest', '-u', share_id_from_url(src_share_url) + ':', "-X", "PUT", "-d", "https://oypt.cdn.iypt.org/%s/%s"%(team,vid),
         url_until_fqdn(src_share_url)+ webdav_path + team + "/" + videoname + "_url.txt"])
