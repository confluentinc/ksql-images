#!/usr/bin/env bash

curl_status=$(curl -X POST -s -o /dev/null -w %{http_code} $KSQL_LISTENERS/ksql -H 'content-type: application/vnd.ksql.v1+json; charset=utf-8' -d '{"ksql":"SHOW TOPICS;"}') 
if [ $curl_status -eq 200 ]; then
  echo "Woohoo! KSQL is up!"
  exit 0
else
  echo -e $(date) " KSQL server query response code: " $curl_status " (waiting for 200)" 
  exit 1
fi 
