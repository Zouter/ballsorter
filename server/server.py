import gevent
from gevent.pywsgi import WSGIServer
from gevent.queue import Queue

from flask import Flask, Response, render_template, request
from flask.json import jsonify

import time
import json

import logging

import os
import signal
import subprocess


# SSE "protocol" is described here: http://mzl.la/UPFyxY
class ServerSentEvent(object):
    def __init__(self, data):
        self.data = data
        self.event = None
        self.id = None
        self.desc_map = {
            self.data : "data",
            self.event : "event",
            self.id : "id"
        }

    def encode(self):
        if not self.data:
            return ""
        lines = ["%s: %s" % (v, k)
                 for k, v in self.desc_map.items() if k]

        return "%s\n\n" % "\n".join(lines)

app = Flask(__name__)
subscriptions = []
total = 0

# Client code consumes like this.
@app.route("/")
def index():
    return render_template("index.html")

initialData = ""

@app.route("/initialize", methods=['POST'])
def initialize():
    global initialData
    initialData = request.get_json()
    print(initialData)
    initialData["signal"] = "initialize"

    for sub in subscriptions:
        sub.put(initialData)

    return "OK"

@app.route("/debug")
def debug():
    return "Currently %d subscriptions" % len(subscriptions)

import datetime
@app.route("/publish", methods=['GET', 'POST'])
def publish():
    start = datetime.datetime.now()
    msg = json.loads(request.get_data().decode("utf-8")) # could actually be skipped if the json is already in the correct format

    add(msg)

    print(datetime.datetime.now() - start)

    return "OK"

def add(msg):
    #def notify():
    for sub in subscriptions[:]:
        sub.put(msg)
    #gevent.spawn(notify)

    return "OK"


from io import BytesIO
import base64
import os
import time

@app.route("/wakeup")
def wakeup():
    return "Hello!"

listeners = []
@app.route("/send", methods=['POST'])
def send():
    msg = request.get_json()
    for listener in listeners:
        listener(msg)

    return "OK"

@app.route("/subscribe")
def subscribe():
    print("new subscriber")
    def gen():
        i = 0.
        q = Queue()
        subscriptions.append(q)
        q.put(initialData)
        try:
            while True:
                i += 0.01
                result = q.get(block=True)
                print("sending...")
                #result = np.random.randint(0, 10, (2, 1)).tolist()
                #result = np.abs((10*np.sin([[i], [i*2]]))).tolist()
                ev = ServerSentEvent(json.dumps(result))
                yield ev.encode()
        except GeneratorExit: # Or maybe use flask signals
            print("lost subscriber")
            subscriptions.remove(q)
        print("lost subscriber")

    return Response(gen(), mimetype="text/event-stream")

process = None
@app.route("/begin")
def begin():
    print("BEGIN BALLS")
    global process
    cmd = "python3 run.py"
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True, cwd=os.getcwd()) 
    return "OK"

@app.route("/stop")
def stop():
    if process is not None:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    print("STOP BALLS!!!")
    return "OK"

@app.route("/quit")
def quit():
    if process is not None:
        stop()
    print("Received quit signal - stopping server")
    server.stop()

    return "Quit"

server = None
def start():
    global server
    app.debug = True

    if server:
        print("Restarting server...")
        server.stop()
    server = WSGIServer(("", 5000), app)
    server.serve_forever()

if __name__ == "__main__":
    start()
    # Then visit http://localhost:5000 to subscribe
    # and send messages by visiting http://localhost:5000/publish
