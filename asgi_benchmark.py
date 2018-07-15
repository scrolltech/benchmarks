import re
import subprocess
from collections import defaultdict, namedtuple
from datetime import datetime
from time import sleep

import requests
from ascii_graph import Pyasciigraph

Server = namedtuple('Server', ['name', 'options'])


SERVERS = {
    'Daphne': Server('daphne', []),
    'Hypercorn': Server('hypercorn', []),
    'Hypercorn-uvloop': Server('hypercorn', ['--uvloop']),
    'Uvicorn': Server('uvicorn', []),
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
    if server.name == 'daphne':
        commands = ['daphne', 'asgi:App', '-b', HOST, '-p', str(PORT)]
    elif server.name == 'uvicorn':
        commands = ['uvicorn', 'asgi:App', '--host', HOST, '--port', str(PORT)]
    else:
        commands = [server.name, 'asgi:App', '-b', "{}:{}".format(HOST, PORT)]
    commands.extend(server.options)
    return subprocess.Popen(
        commands, cwd='servers', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def test_server(server):
    response = requests.get("http://{}:{}/10".format(HOST, PORT))
    assert response.status_code == 200
    response = requests.post("http://{}:{}/".format(HOST, PORT), data={'fib': 10})
    assert response.status_code == 200
    assert response.text == "fib=10"


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
