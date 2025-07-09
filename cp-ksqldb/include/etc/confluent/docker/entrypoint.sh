#!/usr/bin/env bash
#
# Copyright 2025 Confluent Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -e

# Determine the mode based on the first argument
MODE="${1:-server}"

case "$MODE" in
  server)
    echo "===> Starting KSQLDB in server mode..."
    export COMPONENT=ksqldb-server
    exec /etc/confluent/docker-server/run
    ;;
  cli)
    echo "===> Starting KSQLDB in CLI mode..."
    export COMPONENT=ksqldb-cli
    shift
    exec /etc/confluent/docker-cli/run "$@"
    ;;
  examples)
    echo "===> Starting KSQLDB in examples mode..."
    export COMPONENT=ksqldb-examples
    shift
    exec /etc/confluent/docker-examples/run "$*"
    ;;
  *)
    echo "Error: Unknown mode '$MODE'. Valid modes are: server, cli, examples"
    echo ""
    echo "Usage:"
    echo "  Docker run with server mode (default):"
    echo "    docker run <image>"
    echo "    docker run <image> server"
    echo ""
    echo "  Docker run with CLI mode:"
    echo "    docker run -it <image> cli [ksql-server-url]"
    echo "    docker run -it <image> cli http://localhost:8088"
    echo ""
    echo "  Docker run with examples mode:"
    echo "    docker run -it <image> examples"
    echo "    docker run -it <image> examples [command]"
    echo ""
    echo "  Using --entrypoint override:"
    echo "    docker run -it --entrypoint ksql <image> http://localhost:8088"
    echo "    docker run -it --entrypoint /bin/bash <image>"
    exit 1
    ;;
esac