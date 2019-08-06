#!/usr/bin/env bash

if [[ $(curl -s -o /dev/null -w %{http_code} $KSQL_LISTENERS/info) = 200 ]]; then
  echo "Woohoo! KSQL is up!"
  exit 0
else 
  echo -e $(date) "\tKSQL HTTP state: " $(curl -s -o /dev/null -w %{http_code} $KSQL_LISTENERS/info) " (waiting for 200)"
  exit 1
fi
