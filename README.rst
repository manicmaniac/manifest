manifest
========

A WSGI application to distribute ad hoc / in-house iOS apps.


Install
-------

If you use Python 3.4 or higher, there are no prerequisites to install.
Just copy ``manifest.py`` into your preferred web server.

.. Note: Currently this does not work on other Python versions.

Usage
-----

Put ``your_app.ipa`` in the directory named ``static`` which is placed at the same level of hierarchy with ``manifest.py``.
Then access there through a mobile web browser.


Testing
-------

Run ``tests.py``.
