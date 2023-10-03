#!/bin/bash
# Build, test and push cebra container.

set -xe

if [[ -z $(git status --porcelain) ]]; then
  TAG=$(git rev-parse --short HEAD)
else
  TAG=dev
fi

BASENAME=cebra
DOCKERNAME=$BASENAME:$TAG
LATEST=$BASENAME:latest
echo Building $DOCKERNAME

#docker login <your registry>

docker build \
	--build-arg UID=$(id -u) \
	--build-arg GID=$(id -g) \
	--build-arg GIT_HASH=$(git rev-parse HEAD) \
       	-t $DOCKERNAME .
docker tag $DOCKERNAME $LATEST

docker run \
	--gpus 1 \
	-v ${CEBRA_DATADIR:-./data}:/data \
	--env CEBRA_DATADIR=/data \
	--network host \
	-it $DOCKERNAME python -m pytest -vvv tests

#docker push $DOCKERNAME
#docker push $LATEST
