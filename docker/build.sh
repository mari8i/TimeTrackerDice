#!/bin/bash

(
  cd ../backend/timetrackerdice
  docker image build --pull -t registry.mariotti.dev/timetrackerdice:latest -f docker/Dockerfile .
  docker push registry.mariotti.dev/timetrackerdice:latest
)
