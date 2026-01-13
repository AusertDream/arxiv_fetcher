"""Configuration loader using OmegaConf."""

from omegaconf import OmegaConf, DictConfig
from pathlib import Path
from typing import Optional


class ConfigLoader:
    """Load and manage configuration using OmegaConf."""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize config loader.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)

    def load(self, env: str = "default") -> DictConfig:
        """
        Load configuration from YAML file.

        Args:
            env: Environment name (default, production, etc.)

        Returns:
            OmegaConf DictConfig object
        """
        # Load default configuration
        default_config_path = self.config_dir / "default.yaml"

        if not default_config_path.exists():
            raise FileNotFoundError(f"Default config not found: {default_config_path}")

        config = OmegaConf.load(default_config_path)

        # Load environment-specific config if exists
        if env != "default":
            env_config_path = self.config_dir / f"{env}.yaml"
            if env_config_path.exists():
                env_config = OmegaConf.load(env_config_path)
                # Merge configs (env config overrides default)
                config = OmegaConf.merge(config, env_config)

        return config

    def validate(self, config: DictConfig) -> bool:
        """
        Validate configuration structure.

        Args:
            config: Configuration to validate

        Returns:
            True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        required_keys = ['database', 'embedding', 'arxiv', 'search', 'api']

        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config section: {key}")

        # Validate database section
        if 'path' not in config.database or 'collection_name' not in config.database:
            raise ValueError("Database config must have 'path' and 'collection_name'")

        # Validate embedding section
        embedding_keys = ['model_path', 'device', 'normalize', 'batch_size']
        for key in embedding_keys:
            if key not in config.embedding:
                raise ValueError(f"Missing embedding config key: {key}")

        return True


def load_config(config_path: Optional[str] = None, env: str = "default") -> DictConfig:
    """
    Convenience function to load configuration.

    Args:
        config_path: Path to config directory or config file (default: "config")
        env: Environment name

    Returns:
        Configuration dict
    """
    if config_path is None:
        # Try to find config directory relative to current file
        config_path = Path(__file__).parent.parent.parent / "config"
    else:
        config_path = Path(config_path)
        # If a file path was provided, get its parent directory
        if config_path.is_file() or config_path.suffix == '.yaml':
            config_path = config_path.parent

    loader = ConfigLoader(str(config_path))
    config = loader.load(env)
    loader.validate(config)

    return config
