#!/usr/bin/env groovy

dockerfile {
    dockerRepos = ['confluentinc/cp-ksql-server', 'confluentinc/cp-ksql-cli', 'confluentinc/ksql-examples']
    dockerPullDeps = ['confluentinc/cp-base']
    dockerRegistry = '368821881613.dkr.ecr.us-west-2.amazonaws.com/'
    dockerUpstreamTag = '5.1.x-7'
    mvnPhase = 'package'
    mvnSkipDeploy = true
    nodeLabel = 'docker-oraclejdk8-compose'
    dockerPush = true
    slackChannel = '#ksql-eng'
}
