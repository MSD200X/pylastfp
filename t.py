import fplib
import mad
import sys
import urllib
import urllib2
import os
import hashlib
import xml.etree.ElementTree as etree

def readf(f):
    while True:
        out = f.read(100)
        if not out:
            break
        yield out

# http://code.activestate.com/recipes/146306/
def formdata_encode(fields):
    BOUNDARY = '----------form-data-boundary--_$'
    out = []
    for (key, value) in fields.items():
        out.append('--' + BOUNDARY)
        out.append('Content-Disposition: form-data; name="%s"' % key)
        out.append('')
        out.append(value)
    out.append('--' + BOUNDARY + '--')
    out.append('')
    body = '\r\n'.join(out)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body
def formdata_post(url, fields):
    content_type, data = formdata_encode(fields)
    req = urllib2.Request(url, data)
    req.add_header('Content-Type', content_type)
    return urllib2.urlopen(req).read()


def readfp(path):
    f = mad.MadFile(path)
    fpdata = fplib.fingerprint(readf(f), f.samplerate(), 2)
    return f.total_time(), fpdata

def getfpid(path, duration, fpdata):
    url = 'http://www.last.fm/fingerprint/query/'
    params = {
        'artist': '',
        'album': '',
        'track': '',
        'duration': duration/1000,
        'filename': os.path.basename(path),
        'username': '',
        'sha256': hashlib.sha256(path).hexdigest(),
    }
    res = formdata_post('%s?%s' % (url, urllib.urlencode(params)),
                        {'fpdata': fpdata})
    try:
        fpid, status = res.split()[:2]
        fpid = int(fpid)
    except ValueError:
        print 'unparseable response:', res
        return

    if status == 'NEW':
        print 'new fingerprint:', fpid
        return
    elif status == 'FOUND':
        print 'fingerprint found:', fpid
        return fpid
    else:
        print 'unknown status:', res
        return

def getmetadataxml(fpid):
    url = 'http://ws.audioscrobbler.com/2.0/'
    params = {
        'method': 'track.getFingerprintMetadata',
        'fingerprintid': fpid,
        'api_key': '2dc3914abf35f0d9c92d97d8f8e42b43',
    }
    out = urllib.urlopen('%s?%s' % (url, urllib.urlencode(params))).read()
    return out

def parsemetadataxml(xml):
    root = etree.fromstring(xml)
    out = []
    for track in root.find('tracks').findall('track'):
        out.append({
            'rank': track.attrib['rank'],
            'artist': track.find('artist').find('name').text,
            'artist_mbid': track.find('artist').find('mbid').text,
            'title': track.find('name').text,
            'track_mbid': track.find('mbid').text,
        })
    return out

if __name__ == '__main__':
    path = os.path.abspath(sys.argv[1])
    duration, fpdata = readfp(path)
    if not fpdata: sys.exit(1)
    fpid = getfpid(path, duration, fpdata)
    if not fpid: sys.exit(1)
    xml = getmetadataxml(fpid)
    for track in parsemetadataxml(xml):
        print '%s - %s' % (track['artist'], track['title'])
