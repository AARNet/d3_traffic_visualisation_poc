#!/usr/bin/env bash
set -x

IMAGE_NAME="research_visualisation"
REMOTE_HOST="$1"

docker build -t $IMAGE_NAME .
ssh $REMOTE_HOST sudo docker kill $IMAGE_NAME
ssh $REMOTE_HOST sudo docker container rm $IMAGE_NAME
docker save $IMAGE_NAME | pv | ssh $REMOTE_HOST sudo docker load
ssh $REMOTE_HOST sudo docker run --name $IMAGE_NAME -d -p 80:80 $IMAGE_NAME