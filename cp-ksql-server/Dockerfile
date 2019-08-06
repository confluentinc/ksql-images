ARG DOCKER_UPSTREAM_REGISTRY
ARG DOCKER_UPSTREAM_TAG

FROM ${DOCKER_UPSTREAM_REGISTRY}confluentinc/cp-base-new:${DOCKER_UPSTREAM_TAG}

EXPOSE 8088

ENV COMPONENT=ksql-server
ENV KSQL_CLASSPATH=/usr/share/java/${COMPONENT}/*

ARG COMMIT_ID=unknown
LABEL io.confluent.docker.git.id=$COMMIT_ID
ARG BUILD_NUMBER=-1
LABEL io.confluent.docker.build.number=$BUILD_NUMBER
LABEL io.confluent.docker=true

ARG PROJECT_VERSION
ARG ARTIFACT_ID

ADD target/${ARTIFACT_ID}-${PROJECT_VERSION}-package/share/java/${ARTIFACT_ID}/* /usr/share/java/${COMPONENT}/
ADD target/${ARTIFACT_ID}-${PROJECT_VERSION}-package/share/doc/* /usr/share/doc/${ARTIFACT_ID}/
ADD target/dependency/ksql-console-scripts-${PROJECT_VERSION}/* /usr/bin/
ADD target/dependency/ksql-etc-${PROJECT_VERSION}/* /etc/ksql/

COPY include/etc/confluent/docker /etc/confluent/docker

RUN mkdir -p /etc/${COMPONENT} /etc/${COMPONENT}/secrets

RUN chmod +x /etc/confluent/docker/run
RUN chmod +x /etc/confluent/docker/configure
RUN chmod +x /etc/confluent/docker/launch
RUN chmod +x /etc/confluent/docker/ensure

CMD ["/etc/confluent/docker/run"]

# Polling period  : 5 seconds
# Timeout period  :10 seconds (if the polling does not return within this time, treat as a failed poll)
# Start-up period : 2 minutes (during which failures are not counted as failures)
# Retry period    : 8 minutes (after which container is deemed unhealthy)
# All settings can be overriden at run-time in Docker/Docker Compose. 
HEALTHCHECK --start-period=120s --interval=5s --timeout=10s --retries=96 \
	CMD /etc/confluent/docker/healthcheck.sh
