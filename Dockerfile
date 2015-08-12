## building
# docker build -t fwgui .
#
## running
# docker run -p 80:5000 fwgui
#
#
FROM piredtu/openmdao

MAINTAINER Pierre-Elouan Rethore <pire@dtu.dk>

RUN apt-get -y update \
 && apt-get -y install liblapack-dev

RUN mkdir /opt/webapp
WORKDIR /opt/webapp
ADD . /opt/webapp

# Install the webapp
RUN bash -c ". /install/openmdao-0.10.3.2/bin/activate; cd /opt/webapp; python setup.py develop"

# That should not be necessary. Those are unnecessary dependencies in fusedwind 
RUN bash -c ". /install/openmdao-0.10.3.2/bin/activate; pip install ipython algopy"
RUN apt-get -y install python-matplotlib

WORKDIR /opt/webapp/src/wisdem
RUN git checkout develop \
 && git pull


# Done last in order not to have to rebuild all the lib every single time

EXPOSE 5000

CMD o10.3 /opt/webapp/fusedwindGUI/scripts/run.py
