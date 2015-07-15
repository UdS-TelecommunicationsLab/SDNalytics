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

from setuptools import setup, find_packages
import os

if hasattr(os, "link"):
    del os.link

setup(name="sdnalyzer",
      version="2015.8.0",
      packages=find_packages(),
      description="Analytics toolchain for Software Defined Networks.",
      author="Andreas Schmidt",
      author_email="schmidt@nt.uni-saarland.de",
      url="https://www.on.uni-saarland.de",
      entry_points={
          "console_scripts": [
              "sdn-ctl=sdnalyzer.command_line:main",
              "sdn-analyze=sdnalyzer.command_line:analyze",
              "sdn-observe=sdnalyzer.command_line:observe"
          ]
      },
      install_requires=["flask==0.10.1", "pandas==0.15.2", "psycopg2==2.5.4", "sqlalchemy==0.9.9", "scipy==0.13.3"]
      )
