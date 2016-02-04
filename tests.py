#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import plistlib
import shutil
import tempfile
import test.support
import unittest
import zipfile

import manifest


class ManifestTests(unittest.TestCase):
    INFO_PLIST = plistlib.dumps({
        'CFBundleIdentifier': 'com.example.app.spam',
        'CFBundleName': 'spam',
        'CFBundleVersion': '1.0.0',
    }, fmt=plistlib.FMT_BINARY)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        static_dir = os.path.join(self.temp_dir, 'static')
        os.mkdir(static_dir)
        self.ipa_path = os.path.join(static_dir, 'ham.ipa')
        with zipfile.ZipFile(self.ipa_path, 'w') as f:
            f.writestr('Payload/spam.app/Info.plist', self.INFO_PLIST)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_index(self):
        environ = {'HTTP_HOST': 'example.com'}
        with test.support.change_cwd(self.temp_dir):
            body = manifest.index(environ, self._start_response)
            self.assertIn(b'<!DOCTYPE ', body[0])
            self.assertIn(b'</table>', body[0])
            self.assertEqual(self._last_status, '200 OK')
            headers = dict(self._last_headers)
            self.assertEqual(headers['Content-Type'], 'text/html')

    def test_manifest(self):
        environ = {'PATH_INFO': '/static/ham.plist'}
        with test.support.change_cwd(self.temp_dir):
            body = manifest.manifest(environ, self._start_response)
            self.assertIn(b'plist', body[0])
            self.assertEqual(self._last_status, '200 OK')
            headers = dict(self._last_headers)
            self.assertEqual(headers['Content-Type'], 'application/x-plist')

    def test_manifest_with_invalid_path(self):
        environ = {'PATH_INFO': '/'}
        with test.support.change_cwd(self.temp_dir):
            body = manifest.manifest(environ, self._start_response)
            self.assertEqual(body[0], b'404 Not Found')
            self.assertEqual(self._last_status, '404 Not Found')
            headers = dict(self._last_headers)
            self.assertEqual(headers['Content-Type'], 'text/plain')

    def test_static(self):
        environ = {'PATH_INFO': '/static/ham.ipa'}
        with test.support.change_cwd(self.temp_dir):
            body = manifest.static(environ, self._start_response)
            self.assertEqual(len(body[0]), 292)
            self.assertEqual(self._last_status, '200 OK')
            headers = dict(self._last_headers)
            self.assertEqual(headers['Content-Type'],
                             'application/octet-stream')

    def test_static_with_invalid_path(self):
        environ = {'PATH_INFO': '/'}
        with test.support.change_cwd(self.temp_dir):
            body = manifest.static(environ, self._start_response)
            self.assertEqual(body[0], b'404 Not Found')
            self.assertEqual(self._last_status, '404 Not Found')
            headers = dict(self._last_headers)
            self.assertEqual(headers['Content-Type'], 'text/plain')

    def test_not_found(self):
        environ = {}
        body = manifest.not_found(environ, self._start_response)
        self.assertEqual(body, [b'404 Not Found'])
        self.assertEqual(self._last_status, '404 Not Found')
        self.assertEqual(len(self._last_headers), 1)
        self.assertEqual(self._last_headers[0], ('Content-Type', 'text/plain'))

    def test__find_ipas(self):
        ipa_paths = list(manifest._find_ipas(self.temp_dir))
        self.assertEqual(len(ipa_paths), 1)
        self.assertIn(self.ipa_path, ipa_paths)

    def test__get_app_name(self):
        app_name = manifest._get_app_name(self.ipa_path)
        self.assertEqual(app_name, 'spam.app')

    def test__get_ipa_info(self):
        info = manifest._get_ipa_info(self.ipa_path)
        self.assertEqual(info['CFBundleIdentifier'], 'com.example.app.spam')
        self.assertEqual(info['CFBundleName'], 'spam')
        self.assertEqual(info['CFBundleVersion'], '1.0.0')

    def test__get_manifest_url(self):
        environ = {'HTTP_HOST': 'example.com'}
        url = manifest._get_manifest_url(environ, 'static/spam.ipa')
        self.assertEqual(url, 'example.com/static/spam.plist')

    def test__get_modified(self):
        modified = manifest._get_modified(self.ipa_path)
        self.assertGreater(len(modified), 8)

    def _start_response(self, status, headers):
        self._last_status = status
        self._last_headers = headers


if __name__ == '__main__':
    unittest.main()
