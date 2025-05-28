import os
import time
import unittest
import platform
import socket

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
    
    # Set socket timeout globally for Python
    socket.setdefaulttimeout(timeout)
    
    return timeout


def check_cluster_ready(cluster):
    """Check if cluster is ready with enhanced error handling for UBI9"""
    checks = [
        ['kafka', KAFKA_READY.format(brokers=1)],
        ['schema-registry',
            SR_READY.format(host="schema-registry", port="8081")]
    ]
    
    results = []
    for service, check_cmd in checks:
        try:
            print(f"Checking {service} readiness...")
            result = cluster.run_command_on_service(service, check_cmd)
            output = result.decode() if result else ""
            is_ready = 'PASS' in output
            print(f"{service} ready: {is_ready} (output: {output.strip()})")
            results.append(is_ready)
        except Exception as e:
            print(f"Error checking {service}: {e}")
            results.append(False)
    
    return all(results)


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
        cmd = 'curl --connect-timeout 60 --max-time 120 http://%s:%d%s' % (self.server_hostname, self.port, uri)
        return run_cmd(self.client_container, cmd)

    def info(self):
        return self.request('/info').decode()


def retry(op, timeout=900):  # Increased default retry timeout to 15 minutes
    """Enhanced retry function with better error reporting for UBI9"""
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
        # Configure comprehensive Docker timeouts for all architectures
        docker_timeout = configure_docker_timeouts()
        
        print(f"Configured Docker timeout: {docker_timeout}s for platform: {platform.machine()}")
        print(f"Python version: {platform.python_version()}")
        print(f"System: {platform.system()} {platform.release()}")
        
        cls.cluster = utils.TestCluster(
            "ksql-server-test", FIXTURES_DIR, "basic-cluster.yml")
        
        print("Starting cluster...")
        cls.cluster.start()
        
        try:
            start = time.time()
            # Increased cluster ready timeout to match Docker timeouts
            cluster_ready_timeout = docker_timeout
            print(f"Waiting for cluster to be ready (timeout: {cluster_ready_timeout}s)...")
            
            while time.time() - start < cluster_ready_timeout:
                elapsed = int(time.time() - start)
                print(f"Cluster readiness check (elapsed: {elapsed}s)")
                
                if check_cluster_ready(cls.cluster):
                    print(f"Cluster ready after {elapsed}s")
                    return
                    
                print("Cluster not ready yet, waiting 10 seconds...")
                time.sleep(10)  # Check every 10 seconds
            
            print("Final cluster readiness check...")
            assert check_cluster_ready(cls.cluster), "Cluster failed to become ready within timeout"
            
        except Exception as e:
            print(f"Cluster setup failed: {e}")
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
                    print("Cluster shutdown successful")
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
        print("Starting KSQL server test...")
        client = KsqlClient(self.cluster, 'ksqldb-cli', 'ksqldb-server', 8088)
        # Use longer timeout for the actual test
        print("Testing KSQL server info endpoint...")
        result = retry(client.info, timeout=get_docker_timeout())
        print(f"KSQL server info: {result}")
        assert result is not None, "Failed to get KSQL server info"
