#!/usr/bin/env bash
#
# Copyright 2026 Confluent Inc.
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
#
# End-to-end proof that cp-ksqldb-server does not expose an unauthenticated
# remote JMX listener.
#
#   ./verify-jmx-exposure.sh
#
# Builds the image from this repo, stands up a real Kafka, starts real ksqlDB
# servers, and -- from a separate container -- attempts a real unauthenticated
# JMX connection against each. Nothing is stubbed: the assertions are made
# against the JVM's actual command line, its actual listening sockets, and an
# actual remote MBean read.
#
# The published, unpatched image is run as a control so the test demonstrates
# the vulnerability it is guarding against rather than just asserting the fix.
#
# Requires: docker (with compose v2). No internal Confluent access needed --
# the base image and RPMs are both public.

# Deliberately no pipefail: this script leans on `grep -q` and `head -1`, which
# exit early and SIGPIPE their upstream, and under pipefail that reads as a
# failed pipeline.
set -u

BASE_TAG="${BASE_TAG:-7.5.15}"                # cp-base-new / control-image tag
CONFLUENT_VERSION="${CONFLUENT_VERSION:-7.5.15-1}"
PACKAGES_REPO="${PACKAGES_REPO:-https://packages.confluent.io/rpm/7.5}"
PATCHED_IMAGE="cp-ksqldb-server:jmx-verify"
PROBE_IMAGE="cp-ksqldb-server:jmx-probe"
CONTROL_IMAGE="confluentinc/cp-ksqldb-server:${BASE_TAG}"
NETWORK=jmxtest

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPONENT_DIR="$(cd "$HERE/../.." && pwd)"

PASS=0
FAIL=0

log()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32mPASS\033[0m %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf '   \033[31mFAIL\033[0m %s\n' "$*"; FAIL=$((FAIL + 1)); }
info() { printf '        %s\n' "$*"; }

cleanup() {
  docker rm -f jmxtest-default jmxtest-optin jmxtest-noport jmxtest-control >/dev/null 2>&1
  docker compose -f "$HERE/docker-compose.kafka.yml" down -v >/dev/null 2>&1
  docker network rm "$NETWORK" >/dev/null 2>&1
}
trap cleanup EXIT

# ---------------------------------------------------------------- helpers ---

# Print the JMX-related flags the JVM in $1 was actually started with.
jvm_jmx_flags() {
  docker exec "$1" bash -c 'tr "\0" "\n" < /proc/1/cmdline' 2>/dev/null \
    | grep -i 'jmxremote\|rmi.server' | sort
}

# Print the bind address of the listening socket on port $2 inside container $1.
# Hex, as the kernel reports it: 0100007F/0B00007F == 127.0.0.1,
# ...FFFF00000100007F == ::ffff:127.0.0.1, all-zero == wildcard.
listen_addr_for_port() {
  docker exec "$1" bash -c '
    want='"$2"'
    for f in /proc/net/tcp /proc/net/tcp6; do
      while read -r l; do
        set -- $l; [ "$1" = "sl" ] && continue
        p=$((16#${2##*:}))
        if [ "$p" = "$want" ] && [ "$4" = "0A" ]; then echo "${2%%:*}"; fi
      done < $f
    done' 2>/dev/null | head -1
}

is_loopback_addr() {
  case "$1" in
    0100007F|0B00007F|*FFFF00000100007F) return 0 ;;
    *) return 1 ;;
  esac
}

# Real unauthenticated JMX connect from a container that is not the target.
remote_jmx_probe() {
  docker run --rm --network "$NETWORK" "$PROBE_IMAGE" \
    timeout 60 java -cp /probe JmxProbe "$1" \
    2>/dev/null | grep '^JMX_RESULT=' | head -1
}

start_ksql() {
  local name="$1" image="$2"; shift 2
  docker rm -f "$name" >/dev/null 2>&1
  docker run -d --name "$name" --network "$NETWORK" --hostname "$name" \
    -e KSQL_BOOTSTRAP_SERVERS=kafka:39092 \
    -e KSQL_LISTENERS=http://0.0.0.0:8088 \
    "$@" "$image" >/dev/null
  for _ in $(seq 1 100); do
    docker logs "$name" 2>&1 | grep -q "Server up and running" && return 0
    [ "$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null)" = "running" ] || break
    sleep 3
  done
  echo "ksqlDB container $name never came up:" >&2
  docker logs "$name" 2>&1 | tail -20 >&2
  return 1
}

# ------------------------------------------------------------------ setup ---

log "Building $PATCHED_IMAGE from $COMPONENT_DIR/Dockerfile.ubi8"
docker build \
  --build-arg DOCKER_UPSTREAM_REGISTRY= \
  --build-arg DOCKER_UPSTREAM_TAG="$BASE_TAG" \
  --build-arg CONFLUENT_VERSION="$CONFLUENT_VERSION" \
  --build-arg CONFLUENT_PACKAGES_REPO="$PACKAGES_REPO" \
  --build-arg PROJECT_VERSION="${BASE_TAG}-jmx-verify" \
  --build-arg ARTIFACT_ID=cp-ksqldb-server \
  --build-arg GIT_COMMIT="$(git -C "$COMPONENT_DIR" rev-parse --short HEAD 2>/dev/null || echo local)" \
  -f "$COMPONENT_DIR/Dockerfile.ubi8" -t "$PATCHED_IMAGE" "$COMPONENT_DIR" >/dev/null 2>&1 || {
    echo "build failed" >&2; exit 1; }
info "built $PATCHED_IMAGE"

# Compile the probe once, so each scenario's probe is a bare `java` run.
if ! docker build -q -t "$PROBE_IMAGE" -f - "$HERE" >/dev/null 2>&1 <<EOF
FROM $PATCHED_IMAGE
USER root
COPY JmxProbe.java /probe/
RUN javac /probe/JmxProbe.java
EOF
then
  echo "probe build failed" >&2
  exit 1
fi
info "built $PROBE_IMAGE"

log "Starting Kafka"
docker compose -f "$HERE/docker-compose.kafka.yml" up -d >/dev/null 2>&1
for _ in $(seq 1 60); do
  docker exec jmxtest-kafka kafka-broker-api-versions \
    --bootstrap-server kafka:39092 >/dev/null 2>&1 && break
  sleep 2
done
info "kafka ready"

# -------------------------------------------------------------- scenarios ---

log "CONTROL: published unpatched $CONTROL_IMAGE with KSQL_JMX_PORT=1099"
docker pull "$CONTROL_IMAGE" >/dev/null 2>&1
if start_ksql jmxtest-control "$CONTROL_IMAGE" -e KSQL_JMX_PORT=1099; then
  jvm_jmx_flags jmxtest-control | sed 's/^/        /'
  addr=$(listen_addr_for_port jmxtest-control 1099)
  info "port 1099 bound to: ${addr:-<none>}"
  res=$(remote_jmx_probe jmxtest-control:1099)
  info "$res"
  case "$res" in
    JMX_RESULT=REACHABLE*)
      ok "control reproduces the vulnerability (remote unauthenticated JMX succeeds)" ;;
    *)
      bad "control did NOT reproduce the vulnerability -- the test proves nothing" ;;
  esac
fi

log "SCENARIO 1: patched image, KSQL_JMX_PORT=1099, no KSQL_JMX_OPTS"
if start_ksql jmxtest-default "$PATCHED_IMAGE" -e KSQL_JMX_PORT=1099; then
  jvm_jmx_flags jmxtest-default | sed 's/^/        /'

  if docker logs jmxtest-default 2>&1 | grep -q "WARNING: KSQL_JMX_PORT is set but KSQL_JMX_OPTS is not"; then
    ok "operator warning is emitted"
  else
    bad "operator warning was not emitted"
  fi

  if docker logs jmxtest-default 2>&1 | grep -q "docs.confluent.io/platform/current/ksqldb/operate-and-deploy/monitoring.html"; then
    ok "warning points at the monitoring docs"
  else
    bad "warning does not reference the monitoring docs"
  fi

  addr=$(listen_addr_for_port jmxtest-default 1099)
  info "port 1099 bound to: ${addr:-<none>}"
  if is_loopback_addr "$addr"; then
    ok "JMX listener is bound to loopback"
  else
    bad "JMX listener is NOT bound to loopback (addr=${addr:-<none>})"
  fi

  res=$(remote_jmx_probe jmxtest-default:1099)
  info "$res"
  case "$res" in
    JMX_RESULT=UNREACHABLE*) ok "remote JMX connection is refused" ;;
    *)                       bad "remote JMX connection SUCCEEDED -- still exposed" ;;
  esac

  if docker exec jmxtest-default jcmd 1 VM.flags >/dev/null 2>&1; then
    ok "local in-container JVM management still works"
  else
    bad "local in-container JVM management broke"
  fi

  if docker exec jmxtest-default bash -c 'timeout 5 bash -c "</dev/tcp/127.0.0.1/8088"' 2>/dev/null; then
    ok "ksqlDB REST listener unaffected"
  else
    bad "ksqlDB REST listener is not up"
  fi
fi

log "SCENARIO 2: patched image, operator supplies KSQL_JMX_OPTS (opt-in must still work)"
if start_ksql jmxtest-optin "$PATCHED_IMAGE" \
     -e KSQL_JMX_PORT=1099 \
     -e KSQL_JMX_OPTS="-Dcom.sun.management.jmxremote -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false -Dcom.sun.management.jmxremote.rmi.port=1099"; then
  jvm_jmx_flags jmxtest-optin | sed 's/^/        /'

  if docker logs jmxtest-optin 2>&1 | grep -q "WARNING: KSQL_JMX_PORT is set but KSQL_JMX_OPTS is not"; then
    bad "warning was emitted even though the operator supplied KSQL_JMX_OPTS"
  else
    ok "warning correctly suppressed when operator opts in"
  fi

  if jvm_jmx_flags jmxtest-optin | grep -q 'java.rmi.server.hostname='; then
    ok "java.rmi.server.hostname injected for the bridged-network case"
  else
    bad "java.rmi.server.hostname was not injected"
  fi

  if jvm_jmx_flags jmxtest-optin | grep -q 'jmxremote.host=127.0.0.1'; then
    bad "loopback default leaked into operator-supplied opts"
  else
    ok "operator opts are not overridden with the loopback default"
  fi

  res=$(remote_jmx_probe jmxtest-optin:1099)
  info "$res"
  case "$res" in
    JMX_RESULT=REACHABLE*) ok "opt-in remote JMX still works" ;;
    *)                     bad "opt-in remote JMX broke" ;;
  esac
fi

log "SCENARIO 3: patched image, neither KSQL_JMX_PORT nor KSQL_JMX_OPTS"
if start_ksql jmxtest-noport "$PATCHED_IMAGE"; then
  jvm_jmx_flags jmxtest-noport | sed 's/^/        /'
  addr=$(listen_addr_for_port jmxtest-noport 1099)
  if [ -z "$addr" ]; then
    ok "no JMX listener on 1099 when no port is requested"
  else
    bad "unexpected listener on 1099 (addr=$addr)"
  fi
fi

# ----------------------------------------------------------------- result ---

printf '\n\033[1m== Result: %d passed, %d failed\033[0m\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
