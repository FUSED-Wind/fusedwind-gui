# FUSED-Wind Graphical Web Interface

The FUSED-Wind GUI provides a web server based interface to FUSED-Wind assemblies (and OpenMDAO assemblies in general) for
interactive setup and execution of analyses as well as graphical representation of the outputs in a web browser.


## Installing and running on your machine (the hard way)
### Installing on your machine

* Install OpenMDAO
* Install WISDEM (WISDEM, CommonSE, Turbine_CostsSE, Plant_CostsSE, Plant_FinanceSE, Plant_EnergySE)
* Install the additional python libraries

    $ pip install -r webapp/requirements.txt

### Starting the web app

To run the web app locally on your machine activate your OpenMDAO virtual environment and issue the command

    $ python run.py

In a web browser open the page http://localhost:5000/

## Working with Docker (the easier way, if you have docker)

To build the docker image

    $ make build

To run the local image on a server. It will be served on http://<your server>:49501

    $ make run

To run the docker image locally (modifying the files will change the files in
    the docker container too)

    $ make run_local
