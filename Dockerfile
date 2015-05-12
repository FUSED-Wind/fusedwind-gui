# Setup a simple flask webapp

FROM piredtu/seam

MAINTAINER Pierre-Elouan Rethore <pire@dtu.dk>

RUN apt-get update \
 && apt-get install -y -q \
    curl \
    python-all \
    python-pip \
    wget \
 && apt-get clean all \
 && apt-get purge

RUN mkdir /opt/webapp
WORKDIR /opt/webapp

# Install the webapp
ADD ./webapp/requirements.txt /opt/webapp/requirements.txt
RUN mkdir /opt/webapp/uploads
RUN bash -c ". /install/openmdao-0.10.3.2/bin/activate; pip install -r /opt/webapp/requirements.txt"

# Done last in order not to have to rebuild all the lib every single time
ADD ./webapp /opt/webapp

EXPOSE 5000

CMD bash -c ". /install/openmdao-0.10.3.2/bin/activate; python /opt/webapp/app.py"
