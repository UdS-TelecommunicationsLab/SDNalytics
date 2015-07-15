# SDNalytics 

Software Defined Networks Analytics system.

**Authors:** [Andreas Schmidt](mailto:schmidt@nt.uni-saarland.de)

**Website:** [Open Networking @ Saarland University](http://www.on.uni-saarland.de/)

**Institution:** [Telecommuncations Chair](http://www.nt.uni-saarland.de/) - [Saarland University](http://www.uni-saarland.de/)

**Version:** 2015.8.0 - August 2015


## Installation Guide

    # Install Dependencies
    apt-get install python-pip python2.7-dev gfortran libopenblas-dev liblapack-dev libpg-dev postgresql-9.3 postgresql-contrib-9.3
    pip install numpy

    # The following will make the graph tool known. Replace DISTRIBUTION with your distributions name, e.g. trusty.
    printf "deb http://downloads.skewed.de/apt/DISTRIBUTION DISTRIBUTION universe\ndeb-src http://downloads.skewed.de/apt/DISTRIBUTION DISTRIBUTION universe\n" >> /etc/apt/sources.list.d/graph-tool.list
    apt-get update
    apt-get install python-graph-tool


    # Setting up the Database
    sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'psql';"
    sudo -u postgres psql -c "CREATE DATABASE sdn"

    # Install the software
    python setup.py sdist
    cp sdnalytics.default.json /etc/sdnalytics/sdnalytics.json      # copy the default config
    vim /etc/sdnalytics/sdnalytics.json                             # edit the config and adapt
    sdn-ctl setup

## Configuration

The file `/etc/sdnalytics/sdnalytics.json` contains the following important options:

* `connectionString`: It has the form `"postgresql://user:pass@host:port/database"`.
* `pollInterval`: Gives the interval in seconds at which the observer gathers information from the controller.

{
  "pollInterval": 30,
  "controller": {
    "host": "localhost",
    "port": 8080
  },
  "api": {
    "port": 4711,
    "username": "user",
    "password": "pass"
  }
}

## Usage

Now that the application is installed and configured, there are two processes that can be used: `sdn`



## Compatibility

Tested on Ubuntu 14.04. Does most likely work on other Linx systems. Does not work on Windows or Mac.