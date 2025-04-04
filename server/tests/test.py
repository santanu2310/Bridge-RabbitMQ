import logging
import docker  # type: ignore
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Initialize the Docker client
client = docker.DockerClient(
    base_url="unix:///home/santanu/.docker/desktop/docker.sock"
)

container_names = ["localmongo1", "localmongo2", "localmongo3"]
compose_dir = Path(__file__).parent


# Check if the containers is already running
def is_containers_running(container_names):
    try:
        for name in container_names:
            container = client.containers.get(name)
            if container.status != "running":
                return False

        return True
    except docker.errors.NotFound:
        logger.critical("Container Not found 🥺")
        return False


# Start the container if it's not running
def start_container():
    if not is_containers_running(container_names):
        subprocess.run(
            "docker compose up -d",
            shell=True,
            cwd=compose_dir,
        )
        time.sleep(15)
    else:
        logger.info("Containers are already running")


# Run the test function
def run_test():
    command = "uv run pytest"

    result = subprocess.run(command, shell=True)
    if result.returncode == 0:
        print("Test ran successfully.")
    else:
        print("Test failed.")


# Main execution
if __name__ == "__main__":
    start_container()
    run_test()
