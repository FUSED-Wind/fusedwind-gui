# Setup a simple flask webapp

FROM piredtu/seam

MAINTAINER Pierre-Elouan Rethore <pire@dtu.dk>

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
    curl \
    python-all \
    python-pip \
    wget

ADD ./webapp /opt/webapp/
RUN mkdir /opt/webapp/uploads
WORKDIR /opt/webapp
RUN bash -c ". /install/openmdao-0.10.3.2/bin/activate; pip install -r /opt/webapp/requirements.txt"

EXPOSE 5000

CMD bash -c ". /install/openmdao-0.10.3.2/bin/activate; python /opt/webapp/app.py"
