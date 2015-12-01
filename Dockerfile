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
 && apt-get -y install \
    liblapack-dev \
    python-matplotlib

RUN mkdir /opt/webapp
WORKDIR /opt/webapp
ADD . /opt/webapp

# Install the webapp
RUN o10.3 pip install ipython algopy requests==2.6.0
RUN o10.3 python setup.py develop

WORKDIR /opt/webapp/src/wisdem
RUN git checkout develop \
 && git pull

EXPOSE 5000

CMD o10.3 /opt/webapp/fusedwindGUI/scripts/run.py
