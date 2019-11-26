#!/usr/bin/env groovy

dockerfile {
    upstreamProjects = ['confluentinc/common-docker', 'confluentinc/ksql']
    dockerRepos = ['confluentinc/cp-ksql-server', 'confluentinc/cp-ksql-cli', 'confluentinc/ksql-examples']
    dockerPullDeps = ['confluentinc/cp-base-new']
    dockerRegistry = '368821881613.dkr.ecr.us-west-2.amazonaws.com/'
    mvnPhase = 'package integration-test'
    mvnSkipDeploy = true
    nodeLabel = 'docker-oraclejdk8-compose'
    dockerPush = true
    slackChannel = '#ksqldb-alerts'
}
