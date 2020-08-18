# -*- coding: utf-8 -*-
import os

name = "techanim_flow"

_version = os.environ.get("REZ_TM_PACKAGE_VERSION", "0.1.36")
version = _version

build_command = "python -m rezutils build {root}"
private_build_requires = ["rezutils-1"]

authors = ["rafael"]
category = 'int'

requires = [
    "maya-2018"
]

_ignore = [
    "doc",
    "docs",
    "*.pyc",
    ".cache",
    "__pycache__",
    "*.pyproj",
    "*.sln",
    ".vs",
    "template.ini"
]

_environ = {
    "MAYA_MODULE_PATH": ["{root}/python"],
    "PYTHONPATH": [
        "{root}/python"
    ],
    # "TECHANIM_ENV_CONFIG": "{root}/python/techanim_flow/techanim_config.json",
    "TECHANIM_ROOT": "{root}"
}


def commands():
    global env
    global this
    global system
    global expandvars

    environ = this._environ

    for key, value in environ.items():
        if isinstance(value, (tuple, list)):
            [env[key].append(expandvars(v)) for v in value]
        else:
            env[key] = expandvars(value)
