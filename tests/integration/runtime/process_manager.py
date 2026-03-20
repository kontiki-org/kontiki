import socket
import subprocess
import sys
import time
from pathlib import Path


class ServiceProcessManager:
    def __init__(
        self,
        name,
        service_class,
        config_paths,
        log_dir,
        amqp_host="localhost",
        amqp_port=5672,
    ):
        self.name = name
        self.service_class = service_class
        self.config_paths = config_paths
        self.log_dir = Path(log_dir)
        self.amqp_host = amqp_host
        self.amqp_port = amqp_port
        self.process = None
        self.log_file_path = self.log_dir / f"{self.name}.log"
        self._log_handle = None

    def start(self, timeout=15, amqp_ready_timeout=30, max_attempts=4):
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log_handle = self.log_file_path.open("w", encoding="utf-8")
        for attempt in range(1, max_attempts + 1):
            self._start_process()
            try:
                self._wait_until_started(timeout)
                return
            except RuntimeError:
                # RabbitMQ can still flap briefly even after port open.
                if attempt == max_attempts:
                    raise
                self._wait_for_amqp_ready(amqp_ready_timeout)
                time.sleep(0.5 * attempt)

        raise RuntimeError(
            f"Service '{self.name}' could not start after {max_attempts} attempts. "
            f"Check logs: {self.log_file_path}"
        )

    def stop(self, timeout=5):
        if self.process is None:
            return

        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=timeout)

        self.process = None
        if self._log_handle:
            self._log_handle.close()
            self._log_handle = None

    def _wait_until_started(self, timeout):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"Service '{self.name}' exited early. "
                    f"Check logs: {self.log_file_path}"
                )
            if self.log_file_path.exists():
                content = self.log_file_path.read_text(encoding="utf-8")
                if "Service setup completed" in content:
                    return
            time.sleep(0.2)

        raise TimeoutError(
            f"Timeout while waiting for service '{self.name}' startup. "
            f"Check logs: {self.log_file_path}"
        )

    def _start_process(self):
        command = [
            sys.executable,
            "-m",
            "kontiki.runner.__main__",
            self.service_class,
        ]
        for config_path in self.config_paths:
            command.extend(["--config", config_path])

        self.process = subprocess.Popen(
            command,
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
        )

    def _wait_for_amqp_ready(self, timeout):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.create_connection(
                    (self.amqp_host, self.amqp_port), timeout=1.0
                ):
                    return
            except OSError:
                time.sleep(0.2)

        raise TimeoutError(
            f"Timeout while waiting for AMQP broker at "
            f"{self.amqp_host}:{self.amqp_port}"
        )
