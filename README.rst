Benchmark
=========

This allows a simple benchmark comparison of Flask-Gunicorn-gevent VS Flask-Gunicorn-meinheld
worker classes.

Usage
-----

for better results please run it on Jupyter Notebook.
This expects that `wrk <https://github.com/wg/wrk>`_ is installed and
available on the path. If so,::

    pip install -r requirements.txt
    python benchmark.py

