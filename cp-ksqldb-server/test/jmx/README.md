# JMX exposure verification

End-to-end proof that `cp-ksqldb-server` does not ship a remotely reachable,
unauthenticated JMX listener.

```bash
./verify-jmx-exposure.sh
```

One command. It builds the image from this repo, stands up a real Kafka, starts
real ksqlDB servers, and attempts a real unauthenticated JMX connection against
each **from a separate container**. Exits non-zero if any assertion fails.

Requires Docker with Compose v2. No internal Confluent access is needed — both
the `cp-base-new` base image and the Confluent RPMs are public.

## Why it is built this way

Nothing is stubbed. Each assertion is made against something the JVM actually
did:

| Evidence | How it is obtained |
| --- | --- |
| Flags the JVM really received | `/proc/1/cmdline` inside the container |
| Address the listener really bound | `/proc/net/tcp{,6}` inside the container |
| Whether a remote client can really connect | `JmxProbe.java`, run from another container |

The published, unpatched image is run first as a **control**. If the control
does not reproduce the vulnerability, the run fails — otherwise a test that
asserts "remote JMX is refused" would pass just as happily against a broken
network or a container that never started.

## Scenarios

| # | Environment | Expected |
| --- | --- | --- |
| control | published image, `KSQL_JMX_PORT=1099` | remote JMX **reachable** (the bug) |
| 1 | patched, `KSQL_JMX_PORT=1099` | loopback-only bind, remote **refused**, warning logged |
| 2 | patched, `KSQL_JMX_PORT` + explicit `KSQL_JMX_OPTS` | remote **reachable**, warning suppressed |
| 3 | patched, neither set | no listener on 1099 |

Scenario 2 matters as much as scenario 1: hardening the default is only correct
if operators who deliberately enable remote JMX are still able to.

## A note on `com.sun.management.jmxremote.local.only`

`local.only=true` does **not** restrict the remote connector. With a JMX port
set, the JDK still binds the RMI registry to the wildcard address and accepts
remote connections; this was measured on Zulu OpenJDK 11.0.31, the JRE in this
image. The flag that actually confines the listener is
`com.sun.management.jmxremote.host`, which is what `launch` sets.

Anything relying on `local.only` for network confinement is not protected.

## Versions

Overridable by environment variable:

| Variable | Default |
| --- | --- |
| `BASE_TAG` | `7.5.15` |
| `CONFLUENT_VERSION` | `7.5.15-1` |
| `PACKAGES_REPO` | `https://packages.confluent.io/rpm/7.5` |
