# Overview

This package provides `ksql-datagen`: a command-line tool to generate test data.

# Documentation

You can run the command as following:
```shell
$ ksql-datagen quickstart=pageviews bootstrap-server=broker:29092 topic=abcd iterations=200 \
key=pageid
```