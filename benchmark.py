import re
import subprocess
from collections import defaultdict, namedtuple
from datetime import datetime
from time import sleep

import requests
from ascii_graph import Pyasciigraph

Server = namedtuple('Server', ['module', 'gunicorn_worker', 'uvicorn'])

SERVERS = {
    'aiohttp': Server('aiohttp_server', None, None),
    'aiohttp-gunicorn-uvloop': Server('aiohttp_server', 'aiohttp.worker.GunicornUVLoopWebWorker', None),
    'flask': Server('flask_server', None, None),
    'flask-gunicorn-eventlet': Server('flask_server', 'eventlet', None),
    'flask-gunicorn-meinheld': Server('flask_server', 'meinheld.gmeinheld.MeinheldWorker', None),
    'quart': Server('quart_server', None, None),
    'quart-gunicorn': Server('quart_server', 'quart.worker.GunicornWorker', None),
    'quart-gunicorn-uvloop': Server('quart_server', 'quart.worker.GunicornUVLoopWorker', None),
    'quart-uvicorn': Server('quart_server', None, 'asgi_app'),
    'sanic': Server('sanic_server', None, None),
    'sanic-gunicorn-uvloop': Server('sanic_server', 'sanic.worker.GunicornWorker', None),
}

REQUESTS_SECOND_RE = re.compile(r'Requests\/sec\:\s*(?P<reqsec>\d+\.\d+)(?P<unit>[kMG])?')
UNITS = {
    'k': 1_000,
    'M': 1_000_000,
    'G': 1_000_000_000,
}
HOST = '127.0.0.1'
PORT = 5000


def run_server(server):
    if server.gunicorn_worker is not None:
        return subprocess.Popen(
            ['gunicorn', "{}:app".format(server.module), '--worker-class',  server.gunicorn_worker, '-b', "{}:{}".format(HOST, PORT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd='servers',
        )
    elif server.uvicorn is not None:
        return subprocess.Popen(
            ['uvicorn', "{}:{}".format(server.module, server.uvicorn), '-b', "{}:{}".format(HOST, PORT)],
            cwd='servers', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        return subprocess.Popen(
            ['python', "{}.py".format(server.module)], cwd='servers', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def test_server(server):
    response = requests.get("http://{}:{}/10".format(HOST, PORT))
    assert response.status_code == 200
    assert server.module in response.text
    response = requests.post("http://{}:{}/".format(HOST, PORT), data={'fib': 10})
    assert response.status_code == 200
    assert server.module in response.text


def run_benchmark(path, script=None):
    if script is not None:
        script_cmd = "-s {}".format(script)
    else:
        script_cmd = ''
    output = subprocess.check_output(
        "wrk -c 64 -d 30s {} http://{}:{}/{}".format(script_cmd, HOST, PORT, path), shell=True,
    )
    match = REQUESTS_SECOND_RE.search(output.decode())
    requests_second = float(match.group('reqsec'))
    if match.group('unit'):
        requests_second = requests_second * UNITS[match.group('unit')]
    return requests_second


if __name__ == '__main__':
    results = defaultdict(list)
    for name, server in SERVERS.items():
        try:
            print("Testing {} {}".format(name, datetime.now().isoformat()))
            process = run_server(server)
            sleep(5)
            test_server(server)
            results['get'].append((name, run_benchmark('10')))
            results['post'].append((name, run_benchmark('', 'scripts/post.lua')))
        finally:
            process.terminate()
            process.wait()
    graph = Pyasciigraph()
    for key, value in results.items():
        for line in  graph.graph("{} requests/second".format(key), sorted(value, key=lambda result: result[1])):
            print(line)
