# CP-KSQLDB Server Docker Image

This is the Docker image for KSQLDB that combines server and CLI functionality into a single image. The image supports multiple modes of operation through a flexible entrypoint system.

## Overview

The cp-ksqldb-server image provides two distinct modes:
- **Server Mode** - Runs the KSQLDB server (default)
- **CLI Mode** - Runs the KSQLDB interactive CLI

## Modes of Operation

### 1. Server Mode (Default)

Server mode is the default when running the container without arguments or with explicit `ksqldb-server` argument.

```bash
# Default mode - starts KSQLDB server
docker run confluentinc/cp-ksqldb-server

```

When running in server mode:
- Sets `COMPONENT=ksqldb-server`
- Executes `/etc/confluent/docker/server/run`
- Starts the KSQLDB server on default port 8088

### 2. CLI Mode

CLI mode provides an interactive KSQL shell to connect to a KSQLDB server.

```bash
# Connect to a KSQLDB server
docker run -it confluentinc/cp-ksqldb-server ksqldb-cli [ksql-server-url]

# Example: Connect to localhost server
docker run -it confluentinc/cp-ksqldb-server ksqldb-cli http://localhost:8088

# Connect to a remote server
docker run -it confluentinc/cp-ksqldb-server ksqldb-cli http://ksqldb-server:8088
```

When running in CLI mode:
- Sets `COMPONENT=ksqldb-cli`
- Executes `/etc/confluent/docker/cli/run`
- Passes all additional arguments to the KSQL CLI


## Using Custom Entrypoints

You can override the entrypoint for direct access to KSQLDB binaries:

```bash
# Direct server start with custom properties
docker run --entrypoint ksql-server-start confluentinc/cp-ksqldb-server /etc/ksqldb-server/ksqldb-server.properties

# Direct CLI access
docker run -it --entrypoint ksql confluentinc/cp-ksqldb-server http://localhost:8088

# Shell access
docker run -it --entrypoint /bin/bash confluentinc/cp-ksqldb-server
```

