"""
Vector Database Configuration Factory

This module provides a factory function to create the appropriate vector database
based on Dynaconf settings. Supports InMemory and Redis vector databases.

Configuration is loaded from:
    - superlinked_app/config/settings.toml (base configuration)
    - superlinked_app/config/.secrets.toml (local overrides, git-ignored)
    - Environment variables: SEARCHREC__VECTOR_DB_TYPE, SEARCHREC__REDIS_HOST, etc.
    - GCP Secret Manager (production only, via Dynaconf hook)

Configuration Parameters:
    vector_db_type: Type of vector database (inmemory, redis)
    redis_host: Redis server hostname (default: localhost)
    redis_port: Redis server port (default: 6379)
    redis_password: Redis password (optional, loaded from GCP Secret Manager in production)
    redis_username: Redis username (default: default)
    redis_db: Redis database number (default: 0)
    redis_max_connections: Maximum connections in pool (default: 50)
    redis_socket_timeout: Socket timeout in seconds (default: 5)
    redis_socket_connect_timeout: Socket connect timeout in seconds (default: 5)
"""

import logging
from superlinked import framework as sl
from superlinked.framework.dsl.storage.vector_database import VectorDatabase
from superlinked_app.config import settings

logger = logging.getLogger(__name__)


def get_vector_database() -> VectorDatabase:
    """
    Factory function to create the appropriate vector database based on configuration.

    Returns:
        VectorDatabase instance (InMemory or Redis)

    Raises:
        ValueError: If vector_db_type is invalid
        ConnectionError: If Redis connection fails
    """
    db_type = settings.vector_db_type.lower()

    if db_type == "inmemory":
        logger.info("Using InMemoryVectorDatabase")
        return sl.InMemoryVectorDatabase()

    elif db_type == "redis":
        # Get Redis configuration from Dynaconf settings
        redis_host = settings.redis_host
        redis_port = settings.redis_port
        redis_password = settings.redis_password
        redis_username = settings.redis_username
        redis_db = settings.redis_db

        # Redis connection pool settings
        max_connections = settings.redis_max_connections
        socket_timeout = settings.redis_socket_timeout
        socket_connect_timeout = settings.redis_socket_connect_timeout

        logger.info(
            f"Using RedisVectorDatabase: {redis_host}:{redis_port} "
            f"(db={redis_db}, user={redis_username})"
        )

        # Build extra parameters for Redis client
        extra_params = {
            "db": redis_db,
            "max_connections": max_connections,
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
            # Note: Superlinked handles encoding/decoding internally
            # "decode_responses": False,  # Causes issues with Superlinked's encoder
        }

        # Add authentication if password is provided
        if redis_password:
            extra_params["password"] = redis_password
            extra_params["username"] = redis_username
            logger.info("Redis authentication enabled")
        else:
            logger.warning("Redis authentication not configured (password not set)")

        try:
            return sl.RedisVectorDatabase(
                host=redis_host,
                port=redis_port,
                default_query_limit=10,
                **extra_params
            )
        except Exception as e:
            logger.error(f"Failed to initialize Redis vector database: {e}")
            raise ConnectionError(
                f"Could not connect to Redis at {redis_host}:{redis_port}. "
                "Ensure Redis is running and accessible."
            ) from e

    else:
        raise ValueError(
            f"Invalid VECTOR_DB_TYPE: {db_type}. "
            "Supported types: inmemory, redis"
        )


def test_vector_database_connection():
    """
    Test the vector database connection on startup.

    Raises:
        ConnectionError: If connection test fails
    """
    try:
        db = get_vector_database()
        logger.info(f"Vector database initialized successfully: {type(db).__name__}")
        return True
    except Exception as e:
        logger.error(f"Vector database connection test failed: {e}")
        raise


# Run connection test on module import (optional, can be disabled)
if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    test_vector_database_connection()
