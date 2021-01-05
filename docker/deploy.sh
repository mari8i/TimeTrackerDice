#!/usr/bin/env bash

export CI_SECRET_KEY="$1"
export CI_DB_PASSWORD="$2"

DC=docker-compose -f production/docker-compose.yml

$DC pull
$DC down
$DC up -d
