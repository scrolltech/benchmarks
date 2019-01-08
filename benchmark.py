import requests
import re
import subprocess
from collections import defaultdict, namedtuple
from datetime import datetime
from enum import auto, Enum
from time import sleep

import numpy as np
import matplotlib.pyplot as plt 


class ServerType(Enum):
    gunicorn = auto()


Server = namedtuple('Server', ['module', 'server_type', 'settings'])

SERVERS = {
    'flask-gunicorn-gevent': Server('flask_server', ServerType.gunicorn, ['--worker-class', 'gevent']),
    'flask-gunicorn-meinheld': Server('flask_server', ServerType.gunicorn, ['--worker-class', 'meinheld.gmeinheld.MeinheldWorker']),
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
    if server.server_type == ServerType.gunicorn:
        return subprocess.Popen(
            ['gunicorn', "{}:app".format(server.module), '-b', "{}:{}".format(HOST, PORT)] + server.settings,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd='servers',
        )
    else:
        raise ValueError("Unknown server {}".format(server))


def test_server(server):
    response = requests.get("http://{}:{}/10".format(HOST, PORT))
    assert response.status_code == 200
    assert server.module in response.text


def run_benchmark(path, wk, script=None):
    if script is not None:
        script_cmd = "-s {}".format(script)
    else:
        script_cmd = ''
    output = subprocess.check_output(
        "wrk -c {} -d 10s {} http://{}:{}/{}".format(wk, script_cmd, HOST, PORT, path), shell=True,
    )
    match = REQUESTS_SECOND_RE.search(output.decode())
    requests_second = float(match.group('reqsec'))
    if match.group('unit'):
        requests_second = requests_second * UNITS[match.group('unit')]
    return requests_second

if __name__ == '__main__':
    n = 7
    
    results = defaultdict(list)
    fig, ax = plt.subplots(figsize=(20, 10))
    plt.xlabel('Workers')
    plt.ylabel('Requests per second')
    plt.title('Performance')
    index = np.arange(n)
    bar_width = 0.20
    opacity = 0.8

    for i in range(1, n + 1):
        print(f'Running with {2**i} workers.')
        for name, server in SERVERS.items():
            try:
                print("Testing {} {}".format(name, datetime.now().isoformat()))
                process = run_server(server)
                sleep(5)
                test_server(server)
                results[name].append(run_benchmark('10', 2**i))
            finally:
                process.terminate()
                process.wait()
    rects1 = plt.bar(index, results['flask-gunicorn-meinheld'], bar_width,
                 alpha=opacity,
                 color='b',
                 label='Meinheld')
    rects2 = plt.bar(index + bar_width, results['flask-gunicorn-gevent'], bar_width,
                 alpha=opacity,
                 color='g',
                 label='Gevent')
    plt.xticks(index + bar_width, (2**i for i in range(1, n + 1)))
    plt.legend()
    
    def autolabel(rects, xpos='center'):
        xpos = xpos.lower()
        ha = {'center': 'center', 'right': 'left', 'left': 'right'}
        offset = {'center': 0.5, 'right': 0.57, 'left': 0.43} 

        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width()*offset[xpos], 1.01*height,
                   '{}'.format(height), ha=ha[xpos], va='bottom')


    autolabel(rects1, "left")
    autolabel(rects2, "right")

    plt.show()
