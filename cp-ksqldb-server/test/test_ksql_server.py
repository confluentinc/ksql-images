import os
import time
import unittest

import confluent.docker_utils as utils

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(CURRENT_DIR, "fixtures")
KAFKA_READY = (
    "bash -c 'cub kafka-ready -b kafka:39092 {brokers} 40 " +
    "&& echo PASS || echo FAIL'")
SR_READY = "bash -c 'cub sr-ready {host} {port} 20 && echo PASS || echo FAIL'"


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
        self.server_hostname = server
        self.port = port

    def request(self, uri):
        cmd = 'curl --connect-timeout 60 --max-time 120 http://%s:%d%s' % (self.server_hostname, self.port, uri)
        return run_cmd(self.client_container, cmd)

    def info(self):
        return self.request('/info').decode()


def retry(op, timeout=300):
    """Retry function with timeout"""
    start = time.time()
    last_exception = None
    attempt = 0
    
    while time.time() - start < timeout:
        attempt += 1
        try:
            print(f"Retry attempt {attempt} (elapsed: {int(time.time() - start)}s)")
            return op()
        except Exception as e:
            last_exception = e
            print(f"Attempt {attempt} failed: {e}")
            time.sleep(min(5, 2 ** (attempt - 1)))  # Exponential backoff with max 5s
    
    print(f"All retry attempts failed after {timeout}s. Last error: {last_exception}")
    return op()  # Final attempt to get the actual error


class KsqlServerTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        print("Setting up KSQL server test cluster...")
        
        cls.cluster = utils.TestCluster(
            "ksql-server-test", FIXTURES_DIR, "basic-cluster.yml")
        
        print("Starting cluster...")
        cls.cluster.start()
        
        # Wait for cluster to be ready
        print("Waiting for cluster to be ready...")
        start = time.time()
        timeout = 300  # 5 minutes
        
        while time.time() - start < timeout:
            try:
                # Check Kafka
                kafka_result = cls.cluster.run_command_on_service(
                    'kafka', KAFKA_READY.format(brokers=1))
                kafka_ready = 'PASS' in kafka_result.decode()
                
                # Check Schema Registry
                sr_result = cls.cluster.run_command_on_service(
                    'schema-registry', SR_READY.format(host="schema-registry", port="8081"))
                sr_ready = 'PASS' in sr_result.decode()
                
                if kafka_ready and sr_ready:
                    print(f"Cluster ready after {int(time.time() - start)}s")
                    return
                    
                print(f"Waiting for services... Kafka: {kafka_ready}, SR: {sr_ready}")
                time.sleep(10)
                
            except Exception as e:
                print(f"Error checking cluster readiness: {e}")
                time.sleep(10)
        
        raise Exception("Cluster failed to become ready within timeout")

    @classmethod
    def teardown_class(cls):
        print("Shutting down cluster...")
        if hasattr(cls.cluster, 'shutdown'):
            try:
                cls.cluster.shutdown()
                print("Cluster shutdown successful")
            except Exception as e:
                print(f"Cluster shutdown failed: {e}")

    def test_server_start(self):
        print("Starting KSQL server test...")
        client = KsqlClient(self.cluster, 'ksqldb-cli', 'ksqldb-server', 8088)
        
        print("Testing KSQL server info endpoint...")
        result = retry(client.info, timeout=120)
        print(f"KSQL server info: {result}")
        assert result is not None, "Failed to get KSQL server info"
