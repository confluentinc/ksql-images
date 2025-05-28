import os
import time
import unittest
import platform

import confluent.docker_utils as utils

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(CURRENT_DIR, "fixtures")
KAFKA_READY = (
    "bash -c 'cub kafka-ready -b kafka:39092 {brokers} 40 " +
    "&& echo PASS || echo FAIL'")
SR_READY = "bash -c 'cub sr-ready {host} {port} 20 && echo PASS || echo FAIL'"


def is_ubi9_amd64():
    """Check if running on UBI9 AMD64 architecture"""
    try:
        # Check if running on AMD64
        is_amd64 = platform.machine().lower() in ['x86_64', 'amd64']
        
        # Check if running on UBI9 (check for UBI-specific files or environment)
        is_ubi9 = (
            os.path.exists('/etc/redhat-release') and 
            any('ubi' in line.lower() for line in open('/etc/redhat-release', 'r').readlines())
        ) or os.environ.get('UBI_VERSION', '').startswith('9')
        
        return is_amd64 and is_ubi9
    except:
        return False


def get_docker_timeout():
    """Get appropriate Docker timeout based on platform"""
    if is_ubi9_amd64():
        # Increased timeout for UBI9 AMD64 due to known socket timeout issues
        return 300  # 5 minutes instead of default
    return 120  # Default timeout


def check_cluster_ready(cluster):
    checks = [
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

    def request(self, uri):
        cmd = 'curl http://%s:%d%s' % (self.server_hostname, self.port, uri)
        return run_cmd(self.client_container, cmd)

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
        # Configure Docker client with appropriate timeout for UBI9 AMD64
        docker_timeout = get_docker_timeout()
        
        # Set environment variables that docker-compose/docker client will use
        os.environ['COMPOSE_HTTP_TIMEOUT'] = str(docker_timeout)
        os.environ['DOCKER_CLIENT_TIMEOUT'] = str(docker_timeout)
        
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
        # Use longer timeout for shutdown on UBI9 AMD64
        if hasattr(cls.cluster, 'shutdown'):
            if is_ubi9_amd64():
                # For UBI9 AMD64, use a more graceful shutdown with retries
                try:
                    cls.cluster.shutdown()
                except Exception as e:
                    print(f"First shutdown attempt failed: {e}")
                    time.sleep(10)  # Wait before retry
                    try:
                        cls.cluster.shutdown()
                    except Exception as e2:
                        print(f"Second shutdown attempt failed: {e2}")
                        # Force cleanup if needed
                        os.system("docker container prune -f")
            else:
                cls.cluster.shutdown()

    def test_server_start(self):
        client = KsqlClient(self.cluster, 'ksqldb-cli', 'ksqldb-server', 8088)
        retry(client.info)
