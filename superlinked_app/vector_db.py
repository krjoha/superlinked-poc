"""
Vector Database Configuration Factory

This module provides a factory function to create the appropriate vector database
based on environment variables. Supports InMemory and Redis vector databases.

Environment Variables:
    VECTOR_DB_TYPE: Type of vector database (inmemory, redis)
    REDIS_HOST: Redis server hostname (default: localhost)
    REDIS_PORT: Redis server port (default: 6379)
    REDIS_PASSWORD: Redis password (optional)
    REDIS_USERNAME: Redis username (default: default)
    REDIS_DB: Redis database number (default: 0)
    REDIS_MAX_CONNECTIONS: Maximum connections in pool (default: 50)
    REDIS_SOCKET_TIMEOUT: Socket timeout in seconds (default: 5)
"""

import os
import logging
from typing import Union
from superlinked import framework as sl
from superlinked.framework.dsl.storage.vector_database import VectorDatabase

logger = logging.getLogger(__name__)


def get_vector_database() -> VectorDatabase:
    """
    Factory function to create the appropriate vector database based on configuration.

    Returns:
        VectorDatabase instance (InMemory or Redis)

    Raises:
        ValueError: If VECTOR_DB_TYPE is invalid
        ConnectionError: If Redis connection fails
    """
    db_type = os.getenv("VECTOR_DB_TYPE", "inmemory").lower()

    if db_type == "inmemory":
        logger.info("Using InMemoryVectorDatabase")
        return sl.InMemoryVectorDatabase()

    elif db_type == "redis":
        # Get Redis configuration from environment
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD", "")
        redis_username = os.getenv("REDIS_USERNAME", "default")
        redis_db = int(os.getenv("REDIS_DB", "0"))

        # Redis connection pool settings
        max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
        socket_timeout = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
        socket_connect_timeout = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))

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
