import os

from setuptools import setup, find_packages

import os, sys, glob, shutil, platform, subprocess
import pip, commands

def get_options():
    import os, os.path
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-f", "--force", dest="force", help="reinstall even existing plugins", action="store_true", default=False)
    parser.add_option("-U", "--upgrade", dest="upgrade", help="Upgrade all packages to the newest available version", action="store_true", default=False)

    (options, args) = parser.parse_args()

    return options, args

def install(package, options):
    command = ['pip', 'install', '-e', package, '--no-deps --src src']
    if options.force:
        command.append('--force-reinstall')
    elif options.upgrade:
        command.append('--upgrade')

    cmd = ' '.join(command)
    out = os.system(cmd)
    print cmd

options, args = get_options()

# first check whether FUSED-Wind is installed and install if necessary
try:
    import fusedwind
except:
    url = 'git+https://github.com/FUSED-Wind/fusedwind.git@develop#egg=fusedwind'
    install(url, options)
try:
    import sphinx_bootstrap_theme
except:
    cmd = 'pip install sphinx_bootstrap_theme'
    out = os.system(cmd)
    print out

seam_modules = ['SEAM',
                'SEAMTower',
                'SEAMLoads',
                'SEAMRotor',
                'SEAMAero'
                ]

SEAM = "https://gitlab.windenergy.dtu.dk/SEAM/"

wisdem_modules = ['WISDEM',
                  'Turbine_CostsSE',
                  'Plant_CostsSE',
                  'Plant_FinanceSE',
                  'Plant_EnergySE',
                  'DriveSE',
                  'RotorSE',
                  'DriveWPACT',
                  'CommonSE']

WISDEM = 'https://github.com/WISDEM/'


for name in seam_modules:
    try:
        m = __import__(name)
        print 'Module %s already installed in directory %s' % (name, m.__file__.strip('__init.pyc'))
        if options.upgrade:
            url = "git+%s%s.git#egg=%s" % (SEAM, name, name)
            print 'Installing module %s' % name
            install(url, options)
    except:
        url = "git+%s%s.git#egg=%s" % (SEAM, name, name)
        print 'Installing module %s' % name
        install(url, options)

for name in wisdem_modules:
    try:
        m = __import__(name.lower())
        print 'Module %s already installed in directory %s' % (name, m.__file__.strip('__init.pyc'))
        if options.upgrade:
            url = "git+%s%s.git#egg=%s" % (WISDEM, name, name)
            print 'Installing module %s' % name
            install(url, options)
    except:
        url = "git+%s%s.git#egg=%s" % (WISDEM, name, name)
        print 'Installing module %s' % name
        install(url, options)

# create docs index.rst
indexrst = [".. fusedwindGUI_index",
"",
"Welcome to FUSED-Wind's documentation!",
"======================================",
"",
"Contents:",
"",
".. toctree::",
"   :maxdepth: 2",
""]

for name in wisdem_modules:
    indexrst.append('   ' + name.lower() + '/docs/index')
for name in seam_modules:
    indexrst.append('   ' + name.lower() + '/docs/index')

indexrst.extend([
'',
'Indices and tables',
'==================',
'',
'* :ref:`genindex`',
'* :ref:`modindex`',
'* :ref:`search`'])

fid = open(os.path.join('src', 'index.rst'), 'w')
for line in indexrst:
    fid.write(line + '\n')
fid.close()

setup(
  name='fusedwindGUI',
  version='0.1.0',
  description='FUSED-Wind Graphical web interface',
  long_description=('FUSED-Wind Graphical web interface'),
  url='http://github.com/FUSED-Wind/fusedwind-gui',
  license='Apache 2',
  author='',
  author_email='',
  packages=['fusedwindGUI'],
   install_requires=["Flask==0.10.1",
   "wtforms",
   "flask-bootstrap",
   "flask-bower",
   "flask-appconfig",
   "flask-wtf",
   "flask-mail",
   "pyyaml",
   "bokeh==0.10.0",
   "Flask-SQLAlchemy==1.0",
   "Jinja2==2.7.1",
   "MarkupSafe==0.18",
   "gunicorn==18.0",
   "gevent==1.0",
   "requests==1.2.3",
   ],
  include_package_data=True,
  entry_points = {
  'console_scripts': [
    'fusedwindGUI = fusedwindGUI.scripts.run:main'
  ]
  },
  package_data={
    'static': 'fusedwindGUI/static/*',
    'templates': 'fusedwindGUI/templates/*'},
  classifiers=[
    "Private :: Do Not Upload"
  ],
)
