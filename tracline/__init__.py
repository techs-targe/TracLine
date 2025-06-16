"""TracLine v2 - A modern task management system for the command line."""

__version__ = "2.0.2"
__author__ = "techs_targe"
__email__ = "tracline@example.com"

from . import core, db, models, cli, adapters, utils

__all__ = ["core", "db", "models", "cli", "adapters", "utils"]