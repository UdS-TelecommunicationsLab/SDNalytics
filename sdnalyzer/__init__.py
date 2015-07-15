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

import argparse
import logging
import store
import json
import netapi
import threading
import os


def configure_logging():
    logging.basicConfig(filename="/tmp/sdnalyzer.log", level=logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger('').addHandler(console)


def configure_cmdline(command=None):
    parser = argparse.ArgumentParser()
    if command is None:
        parser.add_argument("command", help="Specify one of analyze, observe, init, drop.")
    parser.add_argument("-s, --single", dest="single", action="store_true", default=False, help="Whether the process runs only once.")
    args = parser.parse_args()
    return args


def start_api(command, username, password, port):
    state = netapi.init(command, username, password)
    t = threading.Thread(target=netapi.run, args=[port])
    t.daemon = True
    t.start()
    return state


def init(command=None):
    args = configure_cmdline(command)
    if command is None:
        command = args.command
    single = args.single
    configure_logging()
    logging.debug("Starting sdnalyzer.")

    configuration = None
    config_file_path = "/etc/sdnalytics/sdnalytics.json"

    if not os.path.isfile(config_file_path):
        print "Run sdn-ctl setup before executing sdn-observe or sdn-analyze"
        #"Copy sdnalyzer.default.json to " + config_file_path + " and adapt the file according to your setup. Then start this program again."
        return

    with open(config_file_path) as config_file:
        configuration = json.loads(config_file.read())
        if "connectionString" not in configuration:
            raise Exception("No connection string configured in sdnalyzer.json.")

    store.start(configuration["connectionString"])
    if "api" in configuration:
        if "port" in configuration["api"]:
            api_port = int(configuration["api"]["port"])
        if "username" in configuration["api"]:
            api_username = configuration["api"]["username"]
        if "password" in configuration["api"]:
            api_password = configuration["api"]["password"]

    if command == "observe" or command == "analyze":
        command += "r"

    if command == "setup":
        store.init()
        print "Successfully setup the database. You can now use sdn-analyze and sdn-observe monitor your network."
    elif command == "reset":
        store.drop()
        store.init()
        print "Successfully reset the database. All previously gathered data has been discarded."
    elif command == "observer":
        program_state = start_api(command, api_username, api_password, api_port + 1)

        import observer
        poll_interval = 30
        if "pollInterval" in configuration:
            poll_interval = int(configuration["pollInterval"])

        if "controller" in configuration:
            if "host" in configuration["controller"]:
                controller_host = configuration["controller"]["host"]

            if "port" in configuration["controller"]:
                controller_port = configuration["controller"]["port"]

        program_state.instance = observer.Observer(controller_host, controller_port)
        program_state.instance.observe(single, poll_interval, program_state)
    elif command == "analyzer":
        program_state = start_api(command, api_username, api_password, api_port + 2)
        import analyzer
        program_state.instance = analyzer.Analyzer()
        program_state.instance.analyze(single, program_state)
    elif command == "adhoc":
        import adhoc

        adhoc.run()
    else:
        logging.error("Invalid command {}.".format(command))
    logging.debug("Shut down.")