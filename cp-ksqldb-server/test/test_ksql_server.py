import os
import time
import unittest
import urllib.request

import confluent.docker_utils as utils

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(CURRENT_DIR, "fixtures")
KAFKA_READY = (
    "bash -c 'ub kafka-ready {brokers} 40 -b kafka:39092 " +
    "&& echo PASS || echo FAIL'")
SR_READY = "bash -c 'ub sr-ready {host} {port} 20 && echo PASS || echo FAIL'"


def check_cluster_ready(cluster):
    checks = [
        ['kafka', KAFKA_READY.format(brokers=1)],
        ['schema-registry',
            SR_READY.format(host="schema-registry", port="8081")]
    ]
    return all(
        [('PASS' in cluster.run_command_on_service(*args).decode())
            for args in checks])



class KsqlClient(object):
    def __init__(self, cluster, server, port):
        server_container = cluster.get_container(server)
        networks = server_container.inspect_container['NetworkSettings']['Networks']
        self.server_ip = next(iter(networks.values()))['IPAddress']
        self.port = port

    def request(self, uri):
        url = 'http://%s:%d%s' % (self.server_ip, self.port, uri)
        with urllib.request.urlopen(url) as response:
            return response.read()

    def info(self):
        return self.request('/info').decode()


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
            raise

    @classmethod
    def teardown_class(cls):
        cls.cluster.shutdown()

    def test_server_start(self):
        client = KsqlClient(self.cluster, 'ksqldb-server', 8088)
        retry(client.info)
