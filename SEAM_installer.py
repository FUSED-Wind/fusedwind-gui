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

# first check whether FUSED-Wind is installed and install if necessary
try:
    import fusedwind
except:
    url = 'git+https://github.com/FUSED-Wind/fusedwind.git@develop#egg=fusedwind'
    install(url)

modules = ['SEAM', 'SEAMTower', 'SEAMLoads', 'SEAMRotor','SEAMAero', 'SEAMGeometry', 'SEAMDrivetrain']
SEAM = "https://gitlab.windenergy.dtu.dk/SEAM/"

for name in modules:
    try:
        m = __import__(name)
        print 'Module %s already installed in directory %s' % (name, m.__file__.strip('__init.pyc'))
    except:
        url = "git+%s%s.git#egg=%s" % (SEAM, name, name)
        print 'Installing module %s' % name
        install(url)
