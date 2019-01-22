# -*- coding: utf-8 -*-

# python
import os
import json


TECHANIM_ENV_CONFIG = "TECHANIM_ENV_CONFIG"
TECHANIM_CONFIG_NAME = "techanim_config.json"


def get_environment_config(env_name):
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
        return config


CONFIG = get_environment_config(TECHANIM_ENV_CONFIG)
