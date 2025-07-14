# CP-KSQLDB Unified Docker Image

This is a unified Docker image for KSQLDB that combines server, CLI, and examples functionality into a single image. The image supports multiple modes of operation through a flexible entrypoint system.

## Overview

The cp-ksqldb-server image provides three distinct modes:
- **Server Mode** - Runs the KSQLDB server (default)
- **CLI Mode** - Runs the KSQLDB interactive CLI
- **Examples Mode** - Runs KSQLDB examples and demonstrations

## Modes of Operation

### 1. Server Mode (Default)

Server mode is the default when running the container without arguments or with explicit `ksqldb-server` argument.

```bash
# Default mode - starts KSQLDB server
docker run confluentinc/cp-ksqldb-server

```

When running in server mode:
- Sets `COMPONENT=ksqldb-server`
- Executes `/etc/confluent/docker-server/run`
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
- Executes `/etc/confluent/docker-cli/run`
- Passes all additional arguments to the KSQL CLI

### 3. Examples Mode

Examples mode provides ready-to-run KSQLDB examples and demonstrations.

```bash
# Run examples
docker run -it confluentinc/cp-ksqldb-server ksqldb-examples

# Run examples with specific command
docker run -it confluentinc/cp-ksqldb-server ksqldb-examples [command]
```

When running in examples mode:
- Sets `COMPONENT=ksqldb-examples`
- Executes `/etc/confluent/docker-examples/run`
- Passes any additional arguments as commands

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

