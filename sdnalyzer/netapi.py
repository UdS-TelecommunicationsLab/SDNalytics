# The MIT License (MIT)
# 
# Copyright (c) 2015 Saarland University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# Contributor(s): Andreas Schmidt (Saarland University)
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 
# This license applies to all parts of SDNalytics that are not externally
# maintained libraries.

import flask
from datetime import datetime as dt
from functools import wraps
from flask import request, Response
from common import ProgramState

app = flask.Flask(__name__)

program_state = None
username = "root"
password = ""


# Decorator for Basic Auth. SOURCE: http://flask.pocoo.org/snippets/8/
def check_auth(u, p):
    global username, password
    return u == username and p == password


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


# Routes
@app.route("/status", methods=["GET"])
@requires_auth
def status():
    global program_state
    res = {
        "app": program_state.command,
        "started": program_state.started.isoformat(),
        "healthy": program_state.healthy
    }
    return flask.jsonify(res)

@app.route("/run", methods=["GET"], defaults={ 'task': 'all'})
@app.route("/run/<path:task>", methods=["GET"])
@requires_auth
def run(task):
    global program_state
    if program_state.command != "analyzer":
        return fallback("run")
    else:
        try:
            program_state.instance.run(task)
            res = {
                "command": "Analyzer run " + task,
                "success": True
            }
            return flask.jsonify(res)
        except:
            return fallback("run")


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def fallback(path):
    res = {
        "error": 404,
        "message": "The route /{} you provided is not valid. Try one of these: /status".format(path)
    }
    return flask.jsonify(res)


def init(cmd, user="root", passwd="password"):
    global program_state, username, password
    username = user
    password = passwd

    program_state = ProgramState()
    program_state.command = cmd
    program_state.started = dt.now()
    return program_state


def run(port=5000):
    app.run(host="0.0.0.0", port=port)