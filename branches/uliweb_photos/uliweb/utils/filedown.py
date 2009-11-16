import os
from time import time, mktime
from datetime import datetime
from zlib import adler32
import mimetypes
from werkzeug.utils import http_date
from werkzeug.http import is_resource_modified
from werkzeug import Response, wrap_file

def _opener(filename):
    return (
        open(filename, 'rb'),
        datetime.utcfromtimestamp(os.path.getmtime(filename)),
        int(os.path.getsize(filename))
    )

def _generate_etag(mtime, file_size, real_filename):
    return 'wzsdm-%d-%s-%s' % (
        mktime(mtime.timetuple()),
        file_size,
        adler32(real_filename) & 0xffffffff
    )

def filedown(environ, filename, cache=True, cache_timeout=None):
    guessed_type = mimetypes.guess_type(filename)
    mime_type = guessed_type[0] or 'text/plain'
    f, mtime, file_size = _opener(filename)

    headers = [('Date', http_date())]
    if cache:
        etag = _generate_etag(mtime, file_size, filename)
        headers += [
            ('Etag', '"%s"' % etag),
        ]
        if cache_timeout:
            headers += [
                ('Cache-Control', 'max-age=%d, public' % cache_timeout),
                ('Expires', http_date(time() + cache_timeout))
            ]
        if not is_resource_modified(environ, etag, last_modified=mtime):
            f.close()
            return Response(status=304, headers=headers)
    else:
        headers.append(('Cache-Control', 'public'))

    headers.extend((
        ('Content-Type', mime_type),
        ('Content-Length', str(file_size)),
        ('Last-Modified', http_date(mtime))
    ))
    
    return Response(wrap_file(environ, f), status=200, headers=headers,
        direct_passthrough=True)
