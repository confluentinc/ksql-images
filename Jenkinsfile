#!/usr/bin/env groovy
dockerfile {
    dockerRepos = ['confluentinc/cp-ksqldb-server', 'confluentinc/cp-ksqldb-cli',
      'confluentinc/ksqldb-examples']
    dockerPullDeps = ['confluentinc/cp-base-new']
    dockerRegistry = '368821881613.dkr.ecr.us-west-2.amazonaws.com/'
    mvnPhase = 'package integration-test'
    mvnSkipDeploy = true
    nodeLabel = 'docker-oraclejdk8-compose-swarm'
    dockerPush = true
    slackChannel = '#ksql-alerts'
    cron = ''
    usePackages = true
    cpImages = true
    osTypes = ['ubi8']
    nanoVersion = true
}

