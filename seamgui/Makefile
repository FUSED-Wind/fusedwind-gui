ROOT_DIR := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

default: stop run_local
	sleep 1
	open http://docker:49501/Paraboloid
	docker logs -f seamapp

build:
	docker build -t seamapp .

run:
	docker run -d -p 49501:5000 --name seamapp seamapp

tests:
	docker run seamapp python /opt/webapp/tests.py

stop:
	docker stop seamapp
	docker rm seamapp

run_local:
	docker run -d -p 49501:5000 -v $(ROOT_DIR)/webapp:/opt/webapp --name seamapp seamapp
	docker ps
