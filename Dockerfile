# build -t piredtu/seam .

FROM piredtu/fusedwind

MAINTAINER Pierre-Elouan Rethore <pire@dtu.dk>

RUN mkdir /install/seam
ADD . /install/seam
RUN bash -c ". /install/openmdao-0.10.3.2/bin/activate; cd /install/seam;  pip install -r docker_requirements.txt"
