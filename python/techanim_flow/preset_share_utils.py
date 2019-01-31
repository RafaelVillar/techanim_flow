# -*- coding: utf-8 -*-
"""Utils for creating directories to store, delete, copy presets
from Maya nodes. Using maya as inspiration, this performs a
getattr on a list of attrs and stores them in a json file based on type.

Attributes:
    ALL_USER_DIR_NAME (str): name of the user dir
    FILE_NAMING (str): naming convention for the preset dirs
    NAMEING_REGEX (str): regex to sift through the naming convention
    NOTE_TEMPLATE (str): To display infor to the user
    PRESET_DIR_NAME (str): name of the dir
    PRESET_EXT (str): ext name
    PRESET_PUBLISH_NAME (str): I will give you one guess
    PRESET_SHARE_ENV_NAME (str): ENV name to check for the preset root dir
"""
from __future__ import division
from __future__ import generators
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

# Standard
import os
import re
import ast
import glob
import json
import getpass
import datetime
from functools import wraps

import maya.cmds as cmds

# =============================================================================
# Constants
# =============================================================================
ALL_USER_DIR_NAME = "users"
FILE_NAMING = "{nodetype}_{description}_v{version}.{ext}"
NAMEING_REGEX = "(?P<nodetype>[a-zA-Z]+)_(?P<description>[a-zA-Z]+)_v(?P<ver>\d+)(?P<ext>\.[a-zA-Z0-9]+)$"
PRESET_DIR_NAME = "preset_share"
PRESET_EXT = "preset"
PRESET_PUBLISH_NAME = "publish"
PRESET_SHARE_ENV_NAME = "PRESET_SHARE_BASE_DIR"

NOTE_TEMPLATE = \
"""
user: {user}
origin_scene: {origin_scene}
date: {date}
comment: {comment}

{attr_info}

"""


# =============================================================================
# file i/o
# =============================================================================

def _importData(filePath):
    """Import json data

    Args:
        filePath (str): file path

    Returns:
        dict: json contents
    """
    try:
        with open(filePath, 'r') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(e)


def _exportData(data, filePath):
    """Save out data from dict to a json file

    Args:
        data (dict): data you wish stored
        filePath (str): Have it your way, burgerking.
    """
    try:
        with open(filePath, 'w') as f:
            json.dump(data, f, sort_keys=False, indent=4)
    except Exception as e:
        print(e)


def get_all_user_descriptors(user, nodetype):
    """Get the user desciption from the file names and return a list

    Args:
        user (str): under what user to look for
        nodetype (str): name of the dir to check under

    Returns:
        list: of desciptors
    """
    user_presets_info = get_user_presets_type(user, nodetype)
    key = get_nodetype_dir(get_user_dir(user), nodetype)
    if not user_presets_info.get(key):
        return []
    all_descriptors = []
    for filename in user_presets_info[key]:
        results = split_name(filename)
        all_descriptors.append(results[1])
    return list(set(all_descriptors))


def get_all_publish_descriptors(nodetype):
    """get the descriptors from the publish area

    Args:
        nodetype (str): dir to look under

    Returns:
        list: of destrictors
    """
    pub_presets_info = get_publish_presets_type(nodetype)
    key = get_nodetype_dir(get_publish_dir(), nodetype)
    if not pub_presets_info.get(key):
        return []
    all_descriptors = []
    for filename in pub_presets_info[key]:
        results = split_name(filename)
        all_descriptors.append(results[1])
    return list(set(all_descriptors))


def split_name(name):
    """Split the name using the regex

    Args:
        name (str): name of file

    Returns:
        list: of name broken into re groups
    """
    name = os.path.basename(name)
    x = re.compile(NAMEING_REGEX)
    grp = x.search(name)
    return grp.group("nodetype"), grp.group("description"), grp.group("ver"), grp.group("ext")


def get_highest_version(desired_dir, nodetype, description, versionup=True):
    """Get the hirest version of the file in a dir

    Args:
        desired_dir (str): dir to look for files
        nodetype (str): under dir
        description (str): descriptor from the naming convention
        versionup (bool, optional): version up or get the highest existing

    Returns:
        str: of new file name
    """
    version_str = "{:04d}"
    version = 1
    preset_file_name = FILE_NAMING.format(nodetype=nodetype,
                                          description=description,
                                          version="*",
                                          ext=PRESET_EXT)
    search_dir = os.path.join(desired_dir, preset_file_name)
    found_files = glob.glob(search_dir)
    found_files.sort()
    if not found_files:
        return version_str.format(version)

    highest_ver = ast.literal_eval(split_name(found_files[-1])[2])
    if versionup:
        highest_ver = highest_ver + 1
    return version_str.format(highest_ver)


def save_preset(preset_info, user, comment, description, versionup=True):
    """Save a preset to the users/nodetype dir

    Args:
        preset_info (dict): node information with date, time, comment added
        user (str): getpass.getpuser() user name
        comment (str): comment to be recorded and displayed to other users
        description (str): descriptor to be added in the naming convention
        versionup (bool, optional): save over latest, or version up

    Returns:
        str: output path
    """
    preset_info["description"] = description
    nodetype_dir = get_nodetype_dir(get_user_dir(user),
                                    preset_info["nodetype"])
    version = get_highest_version(nodetype_dir,
                                  preset_info["nodetype"],
                                  description,
                                  versionup=versionup)
    preset_file_name = FILE_NAMING.format(nodetype=preset_info["nodetype"],
                                          description=description,
                                          version=version,
                                          ext=PRESET_EXT)
    output_path = os.path.join(nodetype_dir, preset_file_name)
    print("Exported Preset: {}".format(output_path))

    _exportData(preset_info, output_path)
    return output_path


def publish_preset(src_preset, new_comment=None, new_description=None):
    """Publish the preset file from the user area to the publish area

    Args:
        src_preset (str): source location under user
        new_comment (str, optional): allow the user to change the stored comment
        upon publishing
        new_description (str, optional): same as comment, change on publish
    """
    preset_file_name = os.path.basename(src_preset)
    nodetype, description, ver, ext = split_name(preset_file_name)
    preset_info = _importData(src_preset)
    if new_description:
        description = new_description
    if new_comment:
        preset_info["comment"] = new_comment
    node_pub_dir = get_nodetype_dir(get_publish_dir(), nodetype)
    version = get_highest_version(node_pub_dir,
                                  nodetype,
                                  description,
                                  versionup=True)
    preset_file_name = FILE_NAMING.format(nodetype=nodetype,
                                          description=description,
                                          version=version,
                                          ext=PRESET_EXT)
    preset_dest_dir = os.path.join(node_pub_dir, preset_file_name)
    _exportData(preset_info, preset_dest_dir)
    print("File published!: {}".format(preset_dest_dir))


# =============================================================================
# dir wrangling
# =============================================================================

def in_directory(isSub, directory):
    """isSub under the directory

    Args:
        isSub (str): is this one child of the directory
        directory (str): is the parent of the other

    Returns:
        bool: the lie detector determined that was _____
    """
    # https://stackoverflow.com/questions/3812849/how-to-check-whether-a-directory-is-a-sub-directory-of-another-directory/18115684
    # make both absolute
    directory = os.path.join(os.path.realpath(directory), '')
    isSub = os.path.realpath(isSub)

    # return true, if the common prefix of both is equal to directory
    # e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
    return os.path.commonprefix([isSub, directory]) == directory


def ensure_dir(func):
    """wrapped to make sure that every path querried, returned does actually
    exist

    Args:
        func (function): func to wrap

    Returns:
        function: the fucntion passed
    """
    @wraps(func)
    def make_dirs(*args, **kwargs):
        dir_path = func(*args, **kwargs)
        try:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        except Exception as e:
            print(e)
        finally:
            return dir_path
    return make_dirs


@ensure_dir
def get_base_dir():
    """Get the basedir for the preset sharing to take place.

    Returns:
        str: base dir

    Raises:
        IOError: if the env var is not set, we cannot opperate at all
    """
    dir_path = os.environ.get(PRESET_SHARE_ENV_NAME)
    if not dir_path:
        raise IOError("No directory set in environ for preset share!")
    root_dir = os.path.abspath(dir_path)
    if os.path.basename(root_dir) != PRESET_DIR_NAME:
        root_dir = os.path.join(root_dir, PRESET_DIR_NAME)
    return root_dir


@ensure_dir
def get_all_user_dir():
    """get the root user dir. This is the dir where all users are stored

    Returns:
        str: path
    """
    return os.path.join(get_base_dir(), ALL_USER_DIR_NAME)


@ensure_dir
def get_user_dir(user):
    """get a specific user dir

    Args:
        user (str): desired user

    Returns:
        str: the damn dir
    """
    return os.path.join(get_all_user_dir(), user)


@ensure_dir
def get_publish_dir():
    """get publish directory for presets

    Returns:
        str: path
    """
    return os.path.join(get_base_dir(), PRESET_PUBLISH_NAME)


@ensure_dir
def get_nodetype_dir(desired_dir, nodetype):
    """under publish and every user, there is a dir named for a node type,
    get that dir

    Args:
        desired_dir (str): either user or publish
        nodetype (str): desired nodetype dir

    Returns:
        str: path
    """
    return os.path.join(desired_dir, nodetype)


def get_user_presets(user):
    """walk the directory of the user getting a dictionary of all the presets
    recorded

    Args:
        user (str): desired user

    Returns:
        dict: dirname:[presets]
    """
    specific_user_dir = get_user_dir(user)
    presets = {}
    for dirName, subdirList, fileList in os.walk(specific_user_dir):
        if dirName == specific_user_dir:
            continue
        fileList.sort()
        presets[dirName] = fileList
    return presets


def get_user_presets_type(user, nodetype):
    """get user presets of type

    Args:
        user (str): desired user
        nodetype (str): desired nodeType

    Returns:
        dict: dir: [of presets]
    """
    specific_user_dir = get_user_dir(user)
    return get_presets_by_type(specific_user_dir, nodetype)


def get_publish_presets_type(nodetype):
    """get presets of type from publish dir

    Args:
        nodetype (str): desired nodetype

    Returns:
        list: of gathered presets
    """
    return get_presets_by_type(get_publish_dir(), nodetype)


def get_presets_by_type(desired_dir, nodetype):
    presets = {}
    for dirName, subdirList, fileList in os.walk(desired_dir):
        if dirName == desired_dir:
            continue
        if os.path.basename(dirName) != nodetype:
            continue
        fileList.sort()
        presets[dirName] = fileList
    return presets


def get_all_users():
    return os.listdir(get_all_user_dir())

# =============================================================================
# node info wrangling
# =============================================================================


def get_str_attrs(node, attrs):
    """Maya seemed to make a big deal of getting the str attrs first and then
    numerical, did not see a reason not to follow suit

    Args:
        node (str): name of the desired node
        attrs (list): of attrs to get

    Returns:
        dict: attrname: value
    """
    attr_info = {}
    for attr in attrs:
        plug = "{}.{}".format(node, attr)
        attr_type = cmds.getAttr(plug, sl=True, type=True)
        if attr_type != "string":
            continue
        attr_info[attr] = cmds.getAttr(plug) or ''
    return attr_info


def get_attrs(node, attrs):
    """get numerical attrs without prejudice!

    Args:
        node (str): name of node
        attrs (list): of numerical attrs

    Returns:
        dict: attrname: value
    """
    attr_info = {}
    for attr in attrs:
        plug = "{}.{}".format(node, attr)
        attr_info[attr] = cmds.getAttr(plug)
    return attr_info


def get_attr_info(node):
    """Get str attrs and then numerical

    Args:
        node (str): name of node

    Returns:
        dict: attrname:value
    """
    # These are the attrs gathered when maya saves a preset
    # "listAttr -multi -read -write -visible -hasData";
    str_attrs = cmds.listAttr(node,
                              multi=True,
                              write=True,
                              visible=True,
                              hasData=True)

    # "listAttr -multi -write -scalar -visible -hasData";
    scalar_attrs = cmds.listAttr(node,
                                 multi=True,
                                 write=True,
                                 visible=True,
                                 hasData=True,
                                 scalar=True)

    attr_info = get_str_attrs(node, str_attrs)
    attr_info.update(get_attrs(node, scalar_attrs))

    return attr_info


def get_preset_info(node):
    """Add additional infor to the preset information to display to the user

    Args:
        node (str): desired node

    Returns:
        dict: added values below
    """
    preset_info = {}
    preset_info["node_name"] = node
    preset_info["nodetype"] = cmds.nodeType(node)
    preset_info["origin_scene"] = cmds.file(sn=True, q=True)
    preset_info["attr_info"] = get_attr_info(node)
    preset_info["date"] = datetime.datetime.now().isoformat()
    preset_info["user"] = getpass.getuser()
    return preset_info


def get_selected_info():
    """convenience function, get preset info on select maya node

    Returns:
        dict: preset info
    """
    selected_node = cmds.ls(sl=True)
    if not selected_node:
        cmds.warning("Nothing Selected")
        return None
    return get_preset_info(selected_node[0])


def save_preset_for_node(node, comment, description, user=None):
    """save preset to user area

    Args:
        node (str): name of node
        comment (str): comment from user
        description (str): descriptor used for naming
        user (str, optional): if not provided, will default to currect user,
        I do not really wish to support saving to other users area

    Returns:
        str: path saved at
    """
    if not user:
        user = getpass.getuser()
    preset_info = get_preset_info(node)
    preset_info["comment"] = comment
    return save_preset(preset_info, user, comment, description)


# =============================================================================
# applying preset
# =============================================================================

def apply_preset_file(filePath, node):
    """convenience function to apply a preset from a file to a node

    Args:
        filePath (str): target filepath
        node (str): name of the node
    """
    preset_info = _importData(filePath)
    apply_preset(preset_info, node)


def apply_preset(preset_info, node):
    """apply preset to a node

    Args:
        preset_info (dict): preset to be applied
        node (str): name of node
    """
    unsettable = []
    for attr, value in preset_info["attr_info"].iteritems():
        plug = "{}.{}".format(node, attr)
        # attr_type = cmds.getAttr(plug, typ=True)
        try:
            if type(value) in [unicode, str]:
                cmds.setAttr(plug, value, type="string")
            else:
                cmds.setAttr(plug, value)
        except RuntimeError:
            unsettable.append(plug)
            continue

    note_value = NOTE_TEMPLATE.format(**preset_info)
    try:
        cmds.addAttr(node, ln="notes", dt="string")
    except RuntimeError:
        pass
    cmds.setAttr("{}.notes".format(node), note_value, type="string")
    if unsettable:
        msg = "The following attributes were skipped. \n{}"
        cmds.warning(msg.format(unsettable))
