# FUSED-Wind Graphical Web Interface

The FUSED-Wind GUI provides a web server based interface to FUSED-Wind assemblies (and OpenMDAO assemblies in general) for
interactive setup and execution of analyses as well as graphical representation of the outputs in a web browser.


## Installing and running on your machine (the hard way)
### Installing on your machine

* Install OpenMDAO
* Install the additional python libraries needed by the GUI

    $ pip install -r webapp/requirements.txt

* Install the fusedwind-gui package:

    $ python setup.py install

To be able to edit the source of the package and not have to re-install it instead run:

    $ python setup.py develop

Note that the installer automatically installs all required WISDEM and SEAM packages into the ``src`` directory.

### Building the docs

The documentation for all the installed WISDEM and SEAM modules can be built by navigating to the ``src`` directory and typing:

    $ make html

To view them open ``_build/html/index.html``. To make them visible from the web GUI directly copy them to the ``fusedwindGUI/static`` directory:

    $ cp -r src/_build/html fusedwindGUI/static/docs

TODO: make this step part of the build process.

### Starting the web app

The installed package adds an executable file in your bin directory, so to run the web app locally on your machine activate your OpenMDAO virtual environment and issue the command

    $ fusedwindGUI

which can be issued from any location. In a web browser open the page http://localhost:5000/

## Working with Docker (the easier way, if you have docker)

To build the docker image

    $ docker build -t fwgui .

To run the local image on a server. It will be served on http://<your server>:80

    $ docker run -d -p 80:5000 fwgui

To run the docker image locally (modifying the files will change the files in
    the docker container too). This will only work in a *nix environment.

    $ docker run -d -p 80:5000 -v $(pwd):/mystuff fwgui bash
