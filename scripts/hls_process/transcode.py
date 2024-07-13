from glob import glob
import subprocess
import re
import os
import xml.etree.ElementTree as ET
import hashlib

from .secrets import *

class VideoProperties:
    def __init__(self):
        self.nStreams = None
        self.width = None
        self.height = None
        self.audio_codec = None
        self.video_codec = None
        self.video_bit_rate = None
        
    def __repr__(self):
        return "%d streams, %dx%d, audio %s, video %s @ %d kb/s"%(self.nStreams, self.width, self.height, self.audio_codec, self.video_codec, self.video_bit_rate//1000)


def optimal_scaling(videoproperty):
    if videoproperty.width <= 1920 and videoproperty.height <= 1080:
        return (videoproperty.width, videoproperty.height)
    if videoproperty.width/videoproperty.height > 1920./1080: # more widescreen than 16:9
        scalefactor = 1920./videoproperty.width
        return (int(scalefactor*videoproperty.width), int(scalefactor*videoproperty.height))
    else: # 16:9 or less widescreen
        scalefactor = 1080./videoproperty.height
        return (int(scalefactor*videoproperty.width)//2*2, int(scalefactor*videoproperty.height))


def probe_video(filename):
    proberesult = subprocess.run(['ffprobe', '-loglevel', 'quiet', 
        '-show_entries', 'stream=index,codec_type,codec_name,height,width,bit_rate,pix_fmt', filename],
        capture_output=True)

    probe_xml = proberesult.stdout
    if not b'STREAM' in probe_xml:
        raise ValueError('Unable to find streams in "%s": maybe no video file?'%(str(filename)))
    
    probe_xml = re.sub(b'\[SIDE_DATA\]\n', b'', probe_xml, flags=re.MULTILINE)
    probe_xml = re.sub(b'\[/SIDE_DATA\]\n', b'', probe_xml, flags=re.MULTILINE)
    
    probe_xml = re.sub(b'\[STREAM\]\n', b'\n  <stream ', probe_xml, flags=re.MULTILINE)
    probe_xml = re.sub(b'([^=]*)=(.*)\n', b'\\1="\\2" ', probe_xml, flags=re.MULTILINE)
    probe_xml = re.sub(b'\[/STREAM\]\n', b'/>', probe_xml, flags=re.MULTILINE)
    probe_xml = b'<?xml version="1.0"?>\n<file>'+probe_xml+b'\n</file>'
    root = ET.fromstring(probe_xml.decode('ascii'))

    vf = VideoProperties()
    vf.nStreams = len(root)
    for child in root:
        if not 'codec_type' in child.attrib:
            print('stream without codec_type encountered, skipping!')
            continue
        if child.attrib['codec_type'] == 'video':
            vf.width = float(child.attrib['width'])
            vf.height = float(child.attrib['height'])
            vf.pix_fmt = child.attrib['pix_fmt']
            vf.video_codec = child.attrib['codec_name']
            vf.video_bit_rate = int(child.attrib['bit_rate'])
            if vf.pix_fmt != 'yuv420p':
                print('unexpected pix_fmt "%s" makes transcoding mandatory!'%(str(vf.pix_fmt)))
        elif child.attrib['codec_type'] == 'audio':
            vf.audio_codec = child.attrib['codec_name']
        else:
            print('stream with unknown codec_type "%s" encountered, skipping!'%(str(child.attrib['codec_type'])))
            continue
    return vf

def make_hls(source, destdir, scaling=None):
    print('processing %s'%(source))
    resolutions = []
    for h in [1080,720,540,360]:
        width=int((h/scaling[1])*scaling[0])//2*2
        resolutions.append(f"{width}x{h}")
        print("resolution:",width, h)

    accel="""-hwaccel auto \\
  -vaapi_device /dev/dri/renderD128 \\
  -thread_queue_size 512 \\
  
  ,format=nv12|vaapi,hwupload
  
  -c:v h264_vaapi \\
  
  """

    command = f"""ffmpeg \\
  -i {source} \\
  -filter_complex "
    [0:v] fps=25,split=4 [vA][vB][vC][vD];
    [vA] scale={resolutions[0]} [vFullHD];
    [vB] scale={resolutions[1]} [vHDready];
    [vC] scale={resolutions[2]} [vSD];
    [vD] scale={resolutions[3]} [vSDready];
    [0:a] loudnorm=I=-16:LRA=5:TP=-3,aresample=48000 [a]
   " \\
  -max_interleave_delta 0 \\
  -g:v 50 \\
  -preset:v slow \\
  -map "[vFullHD]" \\
  -b:v:0 1800k -maxrate:v:0 2500k -bufsize:v:0 4096k \\
  -map "[vHDready]" \\
  -b:v:1  800k -maxrate:v:1 1300k -bufsize:v:1 2048k \\
  -map "[vSD]" \\
  -b:v:2  400k -maxrate:v:2  600k -bufsize:v:2 1024k \\
  -map "[vSDready]" \\
  -b:v:3  200k -maxrate:v:3  300k -bufsize:v:3  512k \\
  -map "[a]" \\
  -c:a aac \\
  -b:a:0 128k -ac:a:0 2 -ar:a:0 48000 \\
  -f dash \\
  -hls_playlist 1 \\
  -seg_duration 2 \\
  -init_seg_name 'init_$RepresentationID$.hdr' \\
  -media_seg_name 'segment_$RepresentationID$_$Number$.chk' \\
  -adaptation_sets 'id=0,streams=v id=1,streams=a' \\
  {destdir}/manifest.mpd"""
    
    print(command)
    os.system(command)

for f in glob("src/*/*"):
    print(f)
    safef = f # f.replace(' ','\ ').replace('|','\|').replace('(','\(').replace(')','\)')
    video_properties = probe_video(f)
    print(video_properties)
    video = os.path.split(f)
    team = os.path.split(video[0])[-1]
    videoname = video[-1].split(".")[-2]
    auth = hashlib.blake2b(videoname.encode(), key=authkey, digest_size=16).hexdigest()
    vid = auth+"_"+videoname
    out = os.path.join("hls",team,vid)
    if os.path.exists(out):
        print("processed ", out, " already")
        continue
    try:
        os.makedirs(out, exist_ok=True)
    except Exception as e:
        print(e)
        pass
    make_hls(safef, out, optimal_scaling(video_properties))
    print(out)
    #break
