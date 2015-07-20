import os

from setuptools import setup, find_packages

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
  # install_requires=["Flask==0.10.1",
  # "Flask-SQLAlchemy==1.0",
  # "Jinja2==2.7.1",
  # "MarkupSafe==0.18",
  # "gunicorn==18.0",
  # "gevent==1.0",
  # "requests==1.2.3",
  # ],
  include_package_data=True,
  entry_points = {
  'console_scripts': [
    'fusedwindGUI = fusedwindGUI.scripts.run:main'
  ]
  },
  package_data={
    'static': 'webapp/static/*',
    'templates': 'webapp/templates/*'},
  classifiers=[
    "Private :: Do Not Upload"
  ],
)
