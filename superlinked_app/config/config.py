# Configuration system using Dynaconf with GCP Secret Manager integration
import os
import structlog
from dynaconf import Dynaconf, Validator
from pathlib import Path

logger = structlog.get_logger()

# Get the config directory path
CONFIG_DIR = Path(__file__).parent


def load_gcp_secrets(settings_obj, *args, **kwargs):
    """
    Dynaconf hook to load secrets from GCP Secret Manager in production.

    This hook is automatically called during settings initialization.
    It only runs when ENV_FOR_DYNACONF=production.

    Secrets loaded:
    - api-key: API authentication key for Superlinked
    - redis-password: Redis authentication password (if needed)

    The secrets are expected to be in format:
    projects/{project_id}/secrets/{secret_name}/versions/latest
    """
    current_env = os.getenv("ENV_FOR_DYNACONF", "development")

    if current_env != "production":
        logger.debug("Skipping GCP Secret Manager (not in production environment)")
        return

    try:
        from google.cloud import secretmanager

        # Check if we have GCP project ID
        project_id = getattr(settings_obj, "gcp_project_id", None)
        if not project_id:
            logger.warning("GCP project ID not configured, skipping secret loading")
            return

        client = secretmanager.SecretManagerServiceClient()

        # Load API key
        try:
            api_key_name = f"projects/{project_id}/secrets/api-key/versions/latest"
            response = client.access_secret_version(request={"name": api_key_name})
            api_key = response.payload.data.decode("UTF-8")

            # Set in Dynaconf settings
            settings_obj.api_key = api_key

            # Also set for Superlinked (it uses SERVER__API_KEY env var)
            os.environ["SERVER__API_KEY"] = api_key

            logger.info("Successfully loaded API key from GCP Secret Manager")
        except Exception as e:
            logger.error("Failed to load API key from GCP Secret Manager", error=str(e))
            raise

        # Load Redis password if using Redis in production
        if getattr(settings_obj, "vector_db_type", None) == "redis":
            try:
                redis_password_name = f"projects/{project_id}/secrets/redis-password/versions/latest"
                response = client.access_secret_version(request={"name": redis_password_name})
                redis_password = response.payload.data.decode("UTF-8")

                # Set in Dynaconf settings
                settings_obj.redis_password = redis_password

                # Also set as environment variable
                os.environ["REDIS_PASSWORD"] = redis_password

                logger.info("Successfully loaded Redis password from GCP Secret Manager")
            except Exception as e:
                logger.warning("Failed to load Redis password from GCP Secret Manager", error=str(e))
                # Don't fail if Redis password is not found - it might not be required

    except ImportError:
        logger.error("google-cloud-secret-manager not installed, cannot load secrets from GCP")
        raise
    except Exception as e:
        logger.error("Failed to load secrets from GCP Secret Manager", error=str(e))
        raise


# Initialize Dynaconf
settings = Dynaconf(
    envvar_prefix="SEARCHREC",  # Environment variables: SEARCHREC__FOO=bar
    settings_files=["settings.toml", ".secrets.toml"],  # .secrets.toml for local overrides (git-ignored)
    environments=True,
    env_switcher="ENV_FOR_DYNACONF",  # Use ENV_FOR_DYNACONF=production to switch environments
    load_dotenv=True,
    root_path=CONFIG_DIR,
    validators=[
        # Required settings
        Validator("vector_db_type", is_in=["inmemory", "redis"], default="inmemory"),
        Validator("server_port", gte=1, lte=65535, default=8080),
        Validator("log_level", is_in=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO"),
        Validator("pandas_chunksize", gte=1, default=10),
        Validator("use_test_data", is_type_of=bool, default=False),

        # Redis settings
        Validator("redis_host", default="localhost"),
        Validator("redis_port", gte=1, lte=65535, default=6379),
        Validator("redis_db", gte=0, default=0),
        Validator("redis_username", default="default"),
        Validator("redis_password", default=""),
        Validator("redis_max_connections", gte=1, default=50),
        Validator("redis_socket_timeout", gte=1, default=5),
        Validator("redis_socket_connect_timeout", gte=1, default=5),

        # GCP settings (only required in production)
        Validator("gcp_project_id", must_exist=True, when=Validator("ENV_FOR_DYNACONF", eq="production")),
    ],
)

# Register the GCP Secret Manager hook
settings.configure(dynaconf_hooks=[load_gcp_secrets])
