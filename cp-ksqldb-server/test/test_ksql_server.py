import confluent.docker_utils as utils
import logging
import os
import sys
import time
import unittest
import subprocess

# Route logs to stdout
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(CURRENT_DIR, "fixtures")
KAFKA_READY = (
        "bash -c 'cub kafka-ready {brokers} 40 -z $KAFKA_ZOOKEEPER_CONNECT " +
        "&& echo PASS || echo FAIL'")
ZK_READY = "bash -c 'cub zk-ready {servers} 40 && echo PASS || echo FAIL'"
SR_READY = "bash -c 'cub sr-ready {host} {port} 20 && echo PASS || echo FAIL'"


def check_cluster_ready(cluster):
    checks = [
        ['zookeeper', ZK_READY.format(servers="zookeeper:32181")],
        ['kafka', KAFKA_READY.format(brokers=1)],
        ['schema-registry',
         SR_READY.format(host="schema-registry", port="8081")]
    ]
    return all(
        [('PASS' in cluster.run_command_on_service(*args).decode())
         for args in checks])


class RunCommandException(Exception):
    def __init__(self, exit_code, output):
        super(RunCommandException, self).__init__(
            'Cmd failed with output: ' + output.decode())
        self.exit_code = exit_code
        self.output = output


def run_cmd(container, cmd):
    eid = container.create_exec(cmd)
    output = container.start_exec(eid)
    inspect = container.client.exec_inspect(eid)
    if inspect['ExitCode'] != 0:
        raise RunCommandException(inspect['ExitCode'], output)
    return output


class KsqlClient(object):
    def __init__(self, cluster, client, server, port):
        self.cluster = cluster
        self.client_container = self.cluster.get_container(client)
        server_container = self.cluster.get_container(server)
        self.server_hostname = server_container.name
        self.port = port

    # def request(self, uri):
    #     cmd = 'curl http://%s:%d%s' % (self.server_hostname, self.port, uri)
    #     logger.info(f"running curl command {cmd}")
    #     return run_cmd(self.client_container, cmd).decode()

    def request(self, uri):
        cmd = 'curl http://localhost:%s%s' % (self.port, uri)
        logger.info(f"running curl command {cmd}")
        return subprocess.run(cmd, env=os.environ, check=True, capture_output=True, shell=True, text=True)

    def info(self):
        return self.request('/info')


def retry(op, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        try:
            return op()
        except:
            pass
        time.sleep(1)
    return op()

class KsqlServerTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        logger.info('setup of tests, creating ksql test cluster using docker compose')
        cls.cluster = utils.TestCluster(
            "ksql-server-test", FIXTURES_DIR, "basic-cluster.yml")
        cls.cluster.start()
        try:
            start = time.time()
            while time.time() - start < 600:
                if check_cluster_ready(cls.cluster):
                    return
            assert check_cluster_ready(cls.cluster)
        except:
            cls.cluster.shutdown()

    @classmethod
    def teardown_class(cls):
        cls.cluster.shutdown()

    def test_server_start(self):
        logger.info('running tests')
        client = KsqlClient(self.cluster, 'ksqldb-cli', 'ksqldb-server', 8088)
        retry(client.info, timeout=20)