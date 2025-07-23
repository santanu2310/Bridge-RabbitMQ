import time
import logging
import threading
from enum import Enum
from typing import Any, Dict
from contextlib import contextmanager

from app.core.config import create_s3_client, settings
from app.core.db import SyncDatabase, create_sync_client
from app.core.message_broker import create_bloking_rabbit_connection


logger = logging.getLogger(__name__)


class Dependency(str, Enum):
    db = "db"
    s3_client = "s3_client"
    queue = "queue"


class ConnectionConfig:
    """Configuration for connection retry logic"""

    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    HEALTH_CHECK_TIMEOUT = 5.0


class DependencyManager:
    """Thread-safe dependency manager with connection health checking and auto-reconnection"""

    def __init__(self):
        self._connections: Dict[str, Any] = {}
        self._connection_locks: Dict[str, threading.Lock] = {
            dep.value: threading.Lock() for dep in Dependency
        }
        self._initialized = False
        self._main_lock = threading.Lock()
        self._last_health_check: Dict[str, float] = {}

    def _is_connection_healthy(self, dependency: Dependency) -> bool:
        """Check if a connection is still healthy"""
        connection = self._connections.get(dependency.value)
        if not connection:
            return False

        try:
            if dependency == Dependency.db:
                # Quick ping to MongoDB
                connection.client.server_info()
                return True

            elif dependency == Dependency.s3_client:
                # Simple S3 health check
                connection.head_bucket(Bucket=settings.BUCKET_NAME)
                return True

            elif dependency == Dependency.queue:
                channel = connection.channel()
                channel.close()
                return True

        except Exception as e:
            logger.warning(f"Health check failed for {dependency.value}: {e}")
            return False

        return False

    def _create_connection(self, dependency: Dependency) -> Any:
        """Create a new connection for the specified dependency"""
        logger.info(f"Creating new connection for {dependency.value}")

        if dependency == Dependency.db:
            client = create_sync_client()
            return SyncDatabase(client, settings.DATABASE_NAME)

        elif dependency == Dependency.s3_client:
            return create_s3_client()

        elif dependency == Dependency.queue:
            return create_bloking_rabbit_connection()

        else:
            raise ValueError(f"Unknown dependency: {dependency}")

    def _get_or_create_connection(self, dependency: Dependency) -> Any:
        """Get existing connection or create new one with retry logic"""
        with self._connection_locks[dependency.value]:
            # Check if we need to perform health check
            current_time = time.time()
            last_check = self._last_health_check.get(dependency.value, 0)

            # Perform health check every 30 seconds or if connection doesn't exist
            if (
                current_time - last_check > 30
            ) or dependency.value not in self._connections:
                if dependency.value in self._connections:
                    if not self._is_connection_healthy(dependency):
                        logger.warning(
                            f"Connection unhealthy for {dependency.value}, recreating..."
                        )
                        self._close_single_connection(dependency)

                self._last_health_check[dependency.value] = current_time

            # Create connection if it doesn't exist
            if dependency.value not in self._connections:
                for attempt in range(ConnectionConfig.MAX_RETRIES):
                    try:
                        self._connections[dependency.value] = self._create_connection(
                            dependency
                        )
                        logger.info(
                            f"Successfully created connection for {dependency.value}"
                        )
                        break
                    except Exception as e:
                        logger.error(
                            f"Failed to create {dependency.value} connection (attempt {attempt + 1}): {e}"
                        )
                        if attempt < ConnectionConfig.MAX_RETRIES - 1:
                            time.sleep(
                                ConnectionConfig.RETRY_DELAY * (2**attempt)
                            )  # Exponential backoff
                        else:
                            raise ConnectionError(
                                f"Failed to create {dependency.value} connection after {ConnectionConfig.MAX_RETRIES} attempts"
                            )

            return self._connections[dependency.value]

    def get_dependency(self, dependency: Dependency) -> Any:
        """Get a dependency with automatic reconnection if needed"""
        if not isinstance(dependency, Dependency):
            raise ValueError(f"Invalid dependency type: {type(dependency)}")

        try:
            return self._get_or_create_connection(dependency)
        except Exception as e:
            logger.error(f"Failed to get dependency {dependency.value}: {e}")
            raise

    @contextmanager
    def get_dependency_context(self, dependency: Dependency):
        """Context manager for getting dependencies with automatic cleanup on errors"""
        connection = None
        try:
            connection = self.get_dependency(dependency)
            yield connection
        except Exception as e:
            logger.error(f"Error using dependency {dependency.value}: {e}")
            # Mark connection as potentially unhealthy
            if dependency.value in self._last_health_check:
                self._last_health_check[dependency.value] = 0
            raise

    def _close_single_connection(self, dependency: Dependency):
        """Close a single connection safely"""
        if dependency.value not in self._connections:
            return

        connection = self._connections[dependency.value]

        try:
            if dependency == Dependency.db:
                connection.client.close()
                logger.info("MongoDB connection closed")
            elif dependency == Dependency.queue:
                if hasattr(connection, "close") and not connection.is_closed:
                    connection.close()
                logger.info("RabbitMQ connection closed")
            # S3 client doesn't need explicit closing
        except Exception as e:
            logger.error(f"Error closing {dependency.value}: {e}")
        finally:
            del self._connections[dependency.value]
            if dependency.value in self._last_health_check:
                del self._last_health_check[dependency.value]

    def close_connections(self):
        """Close all connections safely"""
        with self._main_lock:
            for dependency in list(Dependency):
                with self._connection_locks[dependency.value]:
                    self._close_single_connection(dependency)

            self._initialized = False
            logger.info("All connections closed")

    def reset_connection(self, dependency: Dependency):
        """Manually reset a specific connection"""
        with self._connection_locks[dependency.value]:
            self._close_single_connection(dependency)
            logger.info(f"Reset connection for {dependency.value}")


# Global instance
_dependency_manager = None
_manager_lock = threading.Lock()


def get_dependency_manager() -> DependencyManager:
    """Get the global dependency manager instance (thread-safe singleton)"""
    global _dependency_manager
    if _dependency_manager is None:
        with _manager_lock:
            if _dependency_manager is None:
                _dependency_manager = DependencyManager()
    return _dependency_manager
