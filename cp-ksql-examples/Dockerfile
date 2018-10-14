ARG DOCKER_REGISTRY
ARG DOCKER_UPSTREAM_TAG

FROM ${DOCKER_REGISTRY}confluentinc/cp-base-new:${DOCKER_UPSTREAM_TAG}

ARG PROJECT_VERSION
ARG ARTIFACT_ID

ADD target/${ARTIFACT_ID}-${PROJECT_VERSION}-package/share/java/${ARTIFACT_ID}/* /usr/share/java/${ARTIFACT_ID}/
ADD target/${ARTIFACT_ID}-${PROJECT_VERSION}-package/share/doc/* /usr/share/doc/${ARTIFACT_ID}/
ADD target/dependency/ksql-console-scripts-${PROJECT_VERSION}/* /usr/bin/
ADD target/dependency/ksql-etc-${PROJECT_VERSION}/* /etc/ksql/
