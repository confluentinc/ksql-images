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


def get_docker_timeout():
    """Get Docker timeout - increased for UBI9 socket timeout issues affecting both AMD64 and ARM"""
    return 600  # 10 minutes for UBI9 (both AMD64 and ARM)


def configure_docker_timeouts():
    """Configure comprehensive Docker timeout settings"""
    timeout = get_docker_timeout()

    # Set multiple timeout environment variables for comprehensive coverage
    timeout_env_vars = {
        'COMPOSE_HTTP_TIMEOUT': str(timeout),
        'DOCKER_CLIENT_TIMEOUT': str(timeout),
        'DOCKER_TIMEOUT': str(timeout),
        'DOCKERD_TIMEOUT': str(timeout),
        'DOCKER_API_TIMEOUT': str(timeout),
        'DOCKER_SOCKET_TIMEOUT': str(timeout),
        'REQUESTS_TIMEOUT': str(timeout),
        'HTTP_TIMEOUT': str(timeout),
        'URLLIB3_TIMEOUT': str(timeout)
    }

    for var, value in timeout_env_vars.items():
        os.environ[var] = value

    return timeout


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


def retry(op, timeout=900):  # Increased default retry timeout to 15 minutes
    start = time.time()
    while time.time() - start < timeout:
        try:
            return op()
        except:
            pass
        time.sleep(2)  # Increased sleep interval to reduce load
    return op()


class KsqlServerTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        # Configure comprehensive Docker timeouts for all architectures
        docker_timeout = configure_docker_timeouts()

        print(f"Configured Docker timeout: {docker_timeout}s for platform: {platform.machine()}")

        cls.cluster = utils.TestCluster(
            "ksql-server-test", FIXTURES_DIR, "basic-cluster.yml")
        cls.cluster.start()
        try:
            start = time.time()
            # Increased cluster ready timeout to match Docker timeouts
            cluster_ready_timeout = docker_timeout
            while time.time() - start < cluster_ready_timeout:
                if check_cluster_ready(cls.cluster):
                    return
                time.sleep(5)  # Check every 5 seconds instead of 1
            assert check_cluster_ready(cls.cluster)
        except:
            cls.cluster.shutdown()
            raise

    @classmethod
    def teardown_class(cls):
        # Use longer timeout for shutdown with retries for UBI9
        if hasattr(cls.cluster, 'shutdown'):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print(f"Shutdown attempt {attempt + 1}/{max_retries}")
                    cls.cluster.shutdown()
                    break
                except Exception as e:
                    print(f"Shutdown attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(15)  # Wait longer between retries
                    else:
                        print("All shutdown attempts failed, forcing cleanup")
                        # Force cleanup if all attempts fail
                        os.system("docker container prune -f")
                        os.system("docker network prune -f")

    def test_server_start(self):
        client = KsqlClient(self.cluster, 'ksqldb-cli', 'ksqldb-server', 8088)
        # Use longer timeout for the actual test
        retry(client.info, timeout=get_docker_timeout())