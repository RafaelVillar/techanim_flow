# -*- coding: utf-8 -*-
"""Grab the config file for both creator and manager

Attributes:
    CONFIG (dict): configuration from from a json
    TECHANIM_CONFIG_NAME (str): json/config file name
    TECHANIM_ENV_CONFIG (str): env var name
"""

# python
import os
import json

__author__ = "Rafael Villar"
__license__ = "MIT"
__version__ = "1.0.0"
__email__ = "rav@ravrigs.com"
__credits__ = ["Bae Jaechul", "www.studioanima.co.jp/en/"]

# =============================================================================
# constants
# =============================================================================

TECHANIM_ENV_CONFIG = "TECHANIM_ENV_CONFIG"
TECHANIM_CONFIG_NAME = "techanim_config.json"
TECHANIM_CACHE_SESSION = "TECHANIM_CACHE_SESSION_DIR"


def get_techanim_config(env_name):
    """Get the config from the environment, if not get the default from
    the module

    Args:
        env_name (str): name of the environ variable

    Returns:
        dict: the config for the creator and setup manager
    """
    dir_name = os.path.dirname(__file__)
    default_config_path = os.path.join(dir_name, TECHANIM_CONFIG_NAME)
    techanim_config_path = os.environ.get(env_name, default_config_path)
    with open(techanim_config_path, 'r') as f:
        config = json.load(f)
    session_cache_dir = os.environ.get(TECHANIM_CACHE_SESSION, config["cache_dir"])
    config["cache_dir"] = os.path.abspath(session_cache_dir)
    return config


CONFIG = get_techanim_config(TECHANIM_ENV_CONFIG)
