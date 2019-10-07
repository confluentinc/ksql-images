#!/usr/bin/env bash

curl_status=$(curl -s -o /dev/null -w %{http_code} $KSQL_LISTENERS/info) 
if [ $curl_status -eq 200 ]; then
  echo "Woohoo! KSQL is up!"
  exit 0
else
  echo -e $(date) " KSQL server listener HTTP state: " $curl_status " (waiting for 200)" 
  exit 1
fi 
