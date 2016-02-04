#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import plistlib
import re
import textwrap
import time
import zipfile

ENCODING = 'UTF-8'
STATIC_ROOT = os.path.join(os.getcwd(), 'static')


def index(environ, start_response):
    html = textwrap.dedent('''\
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="%(encoding)s">
        <title>%(title)s</title>
    </head>
    <body>
        <h1>%(title)s</h1>
        %(content)s
    </body>
    </html>
    ''')
    partial = textwrap.dedent('''\
    <table>
        <caption>%(name)s</caption>
        <tr>
            <th>bundle identifier</th>
            <td>%(identifier)s</td>
        </tr>
        <tr>
            <th>version</th>
            <td>%(version)s</td>
        </tr>
        <tr>
            <th>modified</th>
            <td>%(modified)s</td>
        </tr>
    </table>
    <a href="itms-services://?action=download-manifest&url=%(url)s">Install</a>
    ''')
    content = ''
    for ipa_path in _find_ipas(STATIC_ROOT):
        info = _get_ipa_info(ipa_path)
        content += partial % {
            'identifier': info.get('CFBundleIdentifier', ''),
            'name': info.get('CFBundleName', ''),
            'version': info.get('CFBundleVersion', ''),
            'modified': _get_modified(ipa_path),
            'url': _get_manifest_url(environ, ipa_path),
        }
    html %= {
        'encoding': ENCODING,
        'title': 'apps',
        'content': content,
    }
    status = '200 OK'
    start_response(status, [('Content-Type', 'text/html')])
    return [bytes(html, ENCODING)]


def manifest(environ, start_response):
    path = environ.get('PATH_INFO').lstrip('/')
    base, _ = os.path.splitext(path)
    ipa_path = base + '.ipa'
    if not os.path.isfile(ipa_path):
        return not_found(environ, start_response)
    info = _get_ipa_info(ipa_path)
    plist = plistlib.dumps({
        'items': [
            {
                'assets': [
                    {
                        'kind': 'software-package',
                        'url': environ.get('REQUEST_URI', ''),
                    },
                ],
                'metadata': {
                    'bundle-identifier': info.get('CFBundleIdentifier', ''),
                    'bundle-version': info.get('CFBundleVersion', ''),
                    'kind': 'software',
                    'subtitle': _get_modified(ipa_path),
                    'title': info.get('CFBundleName', ''),
                },
            },
        ],
    })
    status = '200 OK'
    start_response(status, [('Content-Type', 'application/x-plist')])
    return [plist]


def static(environ, start_response):
    path = environ.get('PATH_INFO').lstrip('/')
    try:
        with open(path, 'rb') as f:
            data = f.read()
    except (IOError, OSError):
        return not_found(environ, start_response)
    else:
        status = '200 OK'
        start_response(status, [('Content-Type', 'application/octet-stream')])
        return [data]


def not_found(environ, start_response):
    status = '404 Not Found'
    start_response(status, [('Content-Type', 'text/plain')])
    return [bytes(status, ENCODING)]


URLS = [
    (r'^$', index),
    (r'^static/.*\.plist$', manifest),
    (r'^%s/' % STATIC_ROOT, static),
]


def app(environ, start_response):
    path = environ.get('PATH_INFO').lstrip('/')
    for pattern, callback in URLS:
        if re.search(pattern, path):
            return callback(environ, start_response)
    return not_found(environ, start_response)


def _find_ipas(root_path):
    for dirpath, dirnames, filenames in os.walk(root_path):
        for filename in filenames:
            if filename.endswith('.ipa'):
                path = os.path.join(dirpath, filename)
                yield path


def _get_app_name(ipa_path):
    app_name_re = re.compile(r'Payload/(.*\.app)/')
    with zipfile.ZipFile(ipa_path) as f:
        filenames = f.namelist()
    for filename in filenames:
        try:
            return app_name_re.match(filename).group(1)
        except AttributeError:
            pass


def _get_ipa_info(ipa_path):
    filename = os.path.basename(ipa_path)
    base, _ = os.path.splitext(filename)
    path = 'Payload/%s/Info.plist' % _get_app_name(ipa_path)
    with zipfile.ZipFile(ipa_path) as f:
        return plistlib.loads(f.read(path))


def _get_manifest_url(environ, ipa_path):
    host = environ.get('HTTP_HOST', '')
    base, _ = os.path.splitext(ipa_path)
    return os.path.join(host, base + '.plist')


def _get_modified(path):
    return time.ctime(os.path.getmtime(path))


if __name__ == '__main__':
    import wsgiref.simple_server
    wsgiref.simple_server.make_server('localhost', 8080, app).serve_forever()
