"""
Main installation script of SEAM

run this script from the root directory of the SEAM package:

$ python setup_all.py

This installs the necessary SEAM models at the same level as
the main SEAM package.
"""


import os, sys, glob, shutil, platform, subprocess
import pip, commands

def install(package):
    command = ['pip', 'install', '-e', package, '--no-deps --src .']
    cmd = ' '.join(command)
    out = commands.getoutput(cmd)
    print out

files = ['SEAM', 'SEAMTower', 'SEAMLoads', 'SEAMRotor']

SEAM = "https://gitlab.windenergy.dtu.dk/SEAM/"

for f in files:
    url = "git+%s%s.git#egg=%s" % (SEAM, f, f)
    print 'URL', url
    install(url)
