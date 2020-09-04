# -*- coding: utf-8 -*-
"""Utils for creating a techanim setup. Deriving most major variables from
a config file.

Attributes:
    CONFIG (dict): Pulled from either default or environment variable
    CONFIG_ATTR (str): attr to help find techanim setups
    DEFAULT_SETUP_OPTIONS (dict): default list of options for wrap, I thought
    this would grow to be more useful when I started, consider removing.
    LOCK_ATTRS (list): list of defaults attrs to lock and hide
    RENDER_INPUT_KEY (str): keys for a config dict
    RENDER_OUTPUT_KEY (str): keys for a config dict
    RENDER_SIM_KEY (str): keys for a config dict
    RIGID_KEY (str): keys for a config dict
"""

# TODO
    # unify all the camel casing on nCloth vs ncloth

# Standard
from __future__ import division
from __future__ import generators
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

# standard
import os
import ast
import imp
import copy
import json
import pprint
import traceback
from functools import wraps

# dcc
import maya.mel as mel
import maya.cmds as cmds

# techanim
from techanim_flow import config_io
reload(config_io)

# =============================================================================
# Constants
# =============================================================================
CONFIG = config_io.CONFIG

RIGID_KEY = "rigid_nodes"
RENDER_SIM_KEY = "render_sim"
RENDER_INPUT_KEY = "render_input"
RENDER_OUTPUT_KEY = "render_output"
ADDITIONAL_RENDER_OUTPUT_KEY = "additional_render_output"
LOCK_ATTRS = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
CONFIG_ATTR = "techanim_config"


# Default options that would be interacted with from the UI
DEFAULT_SETUP_OPTIONS = {"falloffMode": "surface",
                         "exclusiveBind": 1}

WRAP_FALLOW_SETTINGS_DICT = {
    0: "surface",
    1: "volume"
}

TECH_MAP_EXT = "techmap"
WEIGHT_MAP_NAME = "{}.{}"

nCloth_attrs_dict = {
    "thicknessPerVertex": 1,
    "bouncePerVertex": 1,
    "frictionPerVertex": 1,
    "stickinessPerVertex": 1,
    "collideStrengthPerVertex": 1,
    "fieldMagnitudePerVertex": 1,
    "massPerVertex": 1,
    "stretchPerVertex": 1,
    "compressionPerVertex": 1,
    "bendPerVertex": 1,
    "bendAngleDropoffPerVertex": 1,
    "restitutionAnglePerVertex": 1,
    "dampPerVertex": 1,
    "rigidityPerVertex": 1,
    "deformPerVertex": 1,
    "inputAttractPerVertex": 1,
    "restLengthScalePerVertex": 1,
    "wrinklePerVertex": 1,
    "liftPerVertex": 1,
    "dragPerVertex": 1,
    "tangentialDragPerVertex": 1
}


rigid_attrs_dict = {
    "thicknessPerVertex": 1,
    "bouncePerVertex": 1,
    "frictionPerVertex": 1,
    "stickinessPerVertex": 1,
    "collideStrengthPerVertex": 1,
    "fieldMagnitudePerVertex": 1
}


nNODES_ATTR_DICT = {
    "nCloth": nCloth_attrs_dict,
    "nRigid": rigid_attrs_dict
}


# =============================================================================
# Data export
# =============================================================================


def __importData(filePath):
    """Return the contents of a json file. Expecting, but not limited to,
    a dictionary.

    Args:
        filePath (string): path to file

    Returns:
        dict: contents of json file, expected dict
    """
    try:
        with open(filePath, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(e)
        return None


def __exportData(data, filePath):
    """export data, dict, to filepath provided

    Args:
        data (dict): expected dict, not limited to
        filePath (string): path to output json file
    """
    try:
        with open(filePath, "w") as f:
            json.dump(data, f, sort_keys=False, indent=4)
    except Exception as e:
        print(e)

# =============================================================================
# utils
# =============================================================================


def set_default_array_value(nNode, nodeType, attr, length, attr_val=None):
    if not attr_val:
        attr_val = nNODES_ATTR_DICT[nodeType][attr]
    value_array = [attr_val for x in xrange(length)]
    cmds.setAttr("{}.{}".format(nNode, attr), value_array, type="doubleArray")
    return value_array


def get_all_nCloth_nodes(namespace=None):
    """get all nCloth nodes specifically

    Returns:
        list: of nNodes
    """
    if namespace:
        ns = "{}:".format(namespace)
    else:
        ns = ""
    search_key = "{}*{}Shape".format(ns, CONFIG["nCloth_suffix"])
    return cmds.ls(search_key, type="nCloth") or []


def get_all_rigid_nodes(namespace=None):
    """get all nRigid nodes specifically

    Returns:
        list: of nNodes
    """
    if namespace:
        ns = "{}:".format(namespace)
    else:
        ns = ""
    search_key = "{}*{}Shape".format(ns, CONFIG["rigid_suffix"])
    return cmds.ls(search_key, type="nRigid") or []


def get_all_ncloth_objects(namespace=None):
    """get all nodes involved with nuclei in scene

    Returns:
        list: of all nodes, ncloth, nrigid
    """
    return get_all_nCloth_nodes(namespace) + get_all_rigid_nodes(namespace)


def set_default_all_rigid_maps(rigid_nodes=None):
    """default all nRigid nodes specifically, not to be confused with nCloth nodes

    Args:
        nCloth_nodes (list, optional): of nodes to default
    """
    if not rigid_nodes:
        rigid_nodes = get_all_rigid_nodes()
    for rigid in rigid_nodes:
        query_mesh = cmds.listConnections("{}.inputMesh".format(rigid), s=True)[0]
        array_length = cmds.polyEvaluate(query_mesh, v=True)
        for attr, val in rigid_attrs_dict.iteritems():
            set_default_array_value(rigid, "nRigid", attr, array_length, attr_val=val)


def set_default_all_nCloth_maps(nCloth_nodes=None):
    """default all nCloth nodes specifically, not to be confused with nRigid nodes

    Args:
        nCloth_nodes (list, optional): of nodes to default
    """
    if not nCloth_nodes:
        nCloth_nodes = get_all_nCloth_nodes()
    for cloth in nCloth_nodes:
        query_mesh = cmds.listConnections("{}.outputMesh".format(cloth), d=True)[0]
        array_length = cmds.polyEvaluate(query_mesh, v=True)
        for attr, val in nCloth_attrs_dict.iteritems():
            set_default_array_value(cloth, "nCloth", attr, array_length, attr_val=val)


def set_default_perVertex(nodes):
    """sets all the paintable or map'able attributes to perVertex as opposed
    to textures

    Args:
        nodes (list): of nodes to default to perVertex
    """
    skipped_attrs = []
    for node in nodes:
        for attr in cmds.listAttr(node):
            if attr.endswith("MapType"):
                node_plug = "{}.{}".format(node, attr)
                try:
                    cmds.setAttr(node_plug, 0)
                except Exception:
                    skipped_attrs.append(node_plug)
    if skipped_attrs:
        print("Attrs skipped: {}".format(skipped_attrs))


def set_all_maps_default():
    """convenience function to default all ncloth nodes in the scene
    """
    nCloths = get_all_nCloth_nodes()
    nRigids = get_all_rigid_nodes()
    set_default_all_nCloth_maps(nCloths)
    set_default_all_rigid_maps(nRigids)
    set_default_perVertex(nCloths + nRigids)


def get_nNodes_from_shape(shapes):
    """get nCloth nodes from selected shapes

    Args:
        shapes (list): list of shapes

    Returns:
        list: nCloth nodes
    """
    nNodes = []
    for shape in shapes:
        nodes = cmds.listConnections("{}.inMesh".format(shape),
                                     s=True,
                                     sh=True,
                                     type="nCloth") or []
        if nodes:
            # most likely nCloth
            nNodes.extend(nodes)
        else:
            # most likely nRigid
            nodes = cmds.listConnections("{}.worldMesh[0]".format(shape),
                                         sh=True,
                                         d=True,
                                         type="nRigid") or []
            nNodes.extend(nodes)
    return nNodes


def get_nNodes_from_transforms(nodes):
    """get nCloth nodes from any selected transform nodes

    Args:
        nodes (list): list of nodes

    Returns:
        list: ncloth nodes
    """
    nNodes = []
    for node in nodes:
        children = cmds.listRelatives(node,
                                      s=True,
                                      type=["mesh", "nRigid", "nCloth"]) or []
        for child in children:
            child_type = cmds.objectType(child)
            if child_type in ["nRigid", "nCloth"]:
                nNodes.append(child)
            elif child_type in ["mesh"]:
                nNodes.extend(get_nNodes_from_shape([child]))
    return list(set(nNodes))


def default_maps_selected():
    """convenience function to default the maps on the selected nNodes
    """
    all_sel = cmds.ls(sl=True)
    sel_trans = cmds.ls(all_sel, type="transform")
    transform_children = get_nNodes_from_transforms(sel_trans)
    sel_nCloths = cmds.ls(all_sel + transform_children, type="nCloth")
    sel_rigids = cmds.ls(all_sel + transform_children, type="nRigid")

    if sel_rigids:
        set_default_all_rigid_maps(sel_rigids)
    if sel_nCloths:
        set_default_all_nCloth_maps(sel_nCloths)


def get_map_attr_data(nNode, attr):
    """get the data from the map attribute

    Args:
        nNode (str): name of node
        attr (str): name of the attribute to pull from

    Returns:
        list: doublearray information from the map attribute
    """
    return cmds.getAttr("{}.{}".format(nNode, attr))


def get_all_maps_nnode(nNode):
    """get all the weight data from provided node

    Args:
        nNode (str): name of the node

    Returns:
        dict: map data
    """
    nodeType = cmds.nodeType(nNode)
    attr_dict = {}
    for attr in nNODES_ATTR_DICT[nodeType].keys():
        attr_dict[attr] = get_map_attr_data(nNode, attr)

    map_data_dict = {}
    map_data_dict[removeNS(nNode)] = attr_dict

    return map_data_dict


def set_maps_data(nNode, map_data_dict, namespace=None):
    """Set the map data onto the provided node from the provided dict

    Args:
        nNode (str): name of node to apply to
        map_data_dict (dict): source of the map data
    """
    if namespace:
        namespace = "{}:".format(namespace)
    else:
        namespace = ""

    ns_nNode = "{}{}".format(namespace, nNode)
    for attr, val in map_data_dict[nNode].iteritems():
        node_plug = "{}.{}".format(ns_nNode, attr)
        try:
            cmds.setAttr(node_plug, val, type="doubleArray")
        except RuntimeError as e:
            print(node_plug, val, "errored")

def export_weights_to_file(path_dir, nNodes, map_data_dict=None):
    """Export all the maps from provided nCloth nodes to the dir

    Args:
        path_dir (str): directory to export weights to
        nNodes (list): of nodes to export maps from
    """
    if not map_data_dict:
        map_data_dict = {}
    for node in nNodes:
        no_ns_node = removeNS(node)
        fileName = WEIGHT_MAP_NAME.format(no_ns_node, TECH_MAP_EXT)
        filepath = os.path.abspath(os.path.join(path_dir, fileName))
        node_map_data_dict = map_data_dict.get(no_ns_node, get_all_maps_nnode(node))
        __exportData(node_map_data_dict, filepath)


def import_weights_from_files(filepaths, namespace=None):
    """import weight map data from the provided file paths

    Args:
        filepaths (list): of filepaths to weight maps
    """
    for path in filepaths:
        map_data_dict = __importData(path)
        nNode = map_data_dict.keys()[0]
        set_maps_data(nNode, map_data_dict, namespace=namespace)


def run_post_script(script_path):
    """Execute post script after the techanim has been created

    Args:
        script_path (str): path to script to execute
    """
    techanim_post_build = imp.load_source('techanim_post_build', script_path)
    post_step = techanim_post_build.TechanimPostStep()
    try:
        post_step.run()
        msg = "Post build executed successfully."
    except Exception as e:
        msg = "Post build failed to execute."
        print(e)
    finally:
        print(msg)

    return techanim_post_build, post_step


def create_chunk(func):
    """Wrap a function call in a single maya undo chunk

    Args:
        func (function): function to wrap in a single undo chunck
    """
    @wraps(func)
    def open_chunk(*args, **kwargs):
        chunk_name = "{}_undoChunck".format(func.__name__)
        try:
            cmds.undoInfo(chunkName=chunk_name,
                          openChunk=True)
            return func(*args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            raise e

        finally:
            cmds.undoInfo(chunkName=chunk_name, closeChunk=True)

    return open_chunk


def viewport_off(func):
    """
    Shoutout to Mgear
    Decorator - Turn off Maya display while func is running.

    if func will fail, the error will be raised after.

    type: (function) -> function

    """
    @wraps(func)
    def wrap(*args, **kwargs):
        # type: (*str, **str) -> None

        # Turn $gMainPane Off:
        gMainPane = mel.eval('global string $gMainPane; $temp = $gMainPane;')
        cmds.paneLayout(gMainPane, edit=True, manage=False)

        try:
            return func(*args, **kwargs)

        except Exception as e:
            raise e

        finally:
            cmds.paneLayout(gMainPane, edit=True, manage=True)

    return wrap


def locknHide(node, attrs=LOCK_ATTRS):
    """Convenience functions to lock and hide attrs on the provided node

    Args:
        node (str): name of node
        attrs (list, optional): list of attrs
    """
    [cmds.setAttr("{}.{}".format(node, attr),
                  lock=True, k=False) for attr in attrs]


def create_wrap(driver,
                driven,
                weightThreshold=0,
                limitWrapInfluence=0,
                maxDistance=1,
                wrapInflType=2,
                exclusiveBind=1,
                autoWeightThreshold=1,
                renderInfl=0,
                falloffMode=1):

    cmds.optionVar(fv=["weightThreshold", weightThreshold])
    cmds.optionVar(iv=["limitWrapInfluence", limitWrapInfluence])
    cmds.optionVar(iv=["maxDistance", maxDistance])
    cmds.optionVar(iv=["wrapInflType", wrapInflType])
    cmds.optionVar(iv=["exclusiveBind", exclusiveBind])
    cmds.optionVar(iv=["autoWeightThreshold", autoWeightThreshold])
    cmds.optionVar(iv=["renderInfl", renderInfl])
    cmds.optionVar(sv=["falloffMode", WRAP_FALLOW_SETTINGS_DICT[falloffMode]])

    cmds.select(cl=True)
    cmds.select(driven)
    cmds.select(driver, add=True)

    mel.eval("CreateWrap;")

    if isinstance(driven, list):
        driven_node = driven[0]
    else:
        driven_node = driven
    driven_type = cmds.nodeType(driven_node)

    if driven_type == "transform":
        driven_node = cmds.listRelatives(driven_node, shapes=True)[0]
    return cmds.listConnections(driven_node, type="wrap")[0]


def set_info(node, attr, data):
    """Set the provided info on an attr to be collected later

    Args:
        node (str): node to set attr
        attr (str): name of attr
        data (dict): of info to store
    """
    try:
        if not cmds.objExists("{}.{}".format(node, attr)):
            cmds.addAttr(node, ln=attr, dt="string")
    except Exception as e:
        print(e)
    plug = "{}.{}".format(node, attr)
    cmds.setAttr(plug, str(data), type="string")


def get_info(root_node, attr):
    setup_config = cmds.getAttr("{}.{}".format(root_node, attr))
    return ast.literal_eval(setup_config)


def removeNS(name):
    """Convenience function to remove NS: from a string

    Args:
        name (str): name

    Returns:
        str: name without ns
    """
    return name.rpartition(":")[2]


def chunks(aList, n):
    """Yield successive n-sized chunks from l."""
    for i in xrange(0, len(aList), n):
        yield aList[i:i + n]


def create_grouping(grouping_dict, parent=None):
    """recursively create a hierarchy of transforms based on dictionary

    Args:
        grouping_dict (dict): nested dictionary to mimic a hierarchy
        parent (str, optional): for the grouping as we recurse
    """
    for group_name, children_dict in grouping_dict.iteritems():
        cmds.select(cl=True)
        if not cmds.objExists(group_name):
            group_name = cmds.group(n=group_name, em=True)
        if parent:
            cmds.parent(group_name, parent)
        if children_dict:
            create_grouping(children_dict, group_name)
        locknHide(group_name)
    cmds.select(cl=True)


def create_techanim_grouping():
    """convenience function for grating techanim grouping, consults config
    This is a shitty way to do this, but maya does not give you a definive way
    to order a hierarchy. should be fine because these groups are empty.
    """
    grouping_dict = CONFIG["grouping"]
    create_grouping(grouping_dict)
    for order in CONFIG.get("grouping_order", []):
        cmds.parent(order, w=True)
        cmds.parent(order, CONFIG.get("techanim_root"))
        cmds.setAttr("{}.v".format(order), 0)


def create_input_layer(techanim_info, falloffMode=1, exclusiveBind=1, **kwargs):
    """Convenience function to create the input layer

    Args:
        techanim_info (dict): render: sim cage
        falloffMode (int, optional): 1: volume, 0: surface
        exclusiveBind (int, optional): 0: off, 1: on
    """
    populate_connection_layer(techanim_info,
                              CONFIG["input_suffix"],
                              CONFIG["render_input"],
                              CONFIG["sim_input"],
                              wrap=True,
                              falloffMode=falloffMode,
                              exclusiveBind=exclusiveBind)


def create_rigid_nodes_wrap(rigid_nodes_dict,
                            nucleus_node,
                            falloffMode=1,
                            exclusiveBind=1,
                            **kwargs):
    """Wrap rigid/passive geo to cages provided by the user

    Args:
        rigid_nodes_dict (dict): render: cage nodes
        nucleus_node (str): name of nuclues node
        falloffMode (int, optional): wrap options
        exclusiveBind (int, optional): wrap options
        **kwargs: catch all
    """
    direct_connect_dict = {}
    hide_all_nodes = []
    for driver_render, driven_cage in rigid_nodes_dict.iteritems():
        rigid_driver = "{}_{}".format(removeNS(driver_render),
                                      CONFIG["input_layer_name"])
        rigid_driver = cmds.duplicate(driver_render,
                                      n=rigid_driver,
                                      un=False)[0]
        freeze_verticies(rigid_driver)
        cmds.parent(rigid_driver, CONFIG["rigid_input"])
        locknHide(rigid_driver)
        hide_all_nodes.append(rigid_driver)
        # driven --------------------------------------------------------------
        driven_node = "{}_{}".format(removeNS(driven_cage),
                                     CONFIG["input_layer_name"])
        driven_node = cmds.duplicate(driven_cage,
                                     n=driven_node,
                                     un=False)[0]
        direct_connect_dict[driver_render] = [driven_node]
        freeze_verticies(driven_node)
        cmds.parent(driven_node, CONFIG["input_layer_name"])
        locknHide(driven_node)

        cmds.select(cl=True)
        hide_all_nodes.append(driven_node)
        # wraps ---------------------------------------------------------------
        cmds.setAttr("{}.v".format(rigid_driver), 1)
        cmds.setAttr("{}.v".format(driven_node), 1)
        wrapDeformer = create_wrap(rigid_driver,
                                   driven_node,
                                   exclusiveBind=exclusiveBind,
                                   falloffMode=falloffMode)
        cmds.rename(wrapDeformer, "{}_wrap".format(rigid_driver))
        cmds.select(cl=True)

    # duplicate and populate the layers of the techanim setup
    sim_index = CONFIG["grouping_order"].index(CONFIG["sim_layer"])
    for driver_render, driven_cage in rigid_nodes_dict.iteritems():
        for layer in CONFIG["grouping_order"][1:sim_index + 1]:
            driven_node = "{}_{}".format(removeNS(driven_cage), layer)
            if layer == CONFIG["sim_layer"]:
                driven_node = "{}_{}{}{}".format(driven_node,
                                                 layer,
                                                 CONFIG["rigid_suffix"],
                                                 CONFIG["nCloth_output_suffix"])
            driven_node = cmds.duplicate(driven_cage,
                                         n=driven_node,
                                         un=False)[0]
            freeze_verticies(driven_node)
            cmds.parent(driven_node, layer)
            locknHide(driven_node)
            # on sim layer, make it a rigid object
            if layer == CONFIG["sim_layer"]:
                cmds.select(cl=True)
                cmds.select(driven_node, nucleus_node)
                rigid_shape = mel.eval("makeCollideNCloth;")[0]
                rigid_trans = cmds.listRelatives(rigid_shape, p=True)[0]
                rigid_name = driven_node.replace(CONFIG["nCloth_output_suffix"],
                                                "")
                rigid_trans = cmds.rename(rigid_trans, rigid_name)
                cmds.parent(rigid_trans, layer)
                locknHide(rigid_trans)

            hide_all_nodes.append(driven_node)
            # direct connection -----------------------------------------------
            last_node = direct_connect_dict[driver_render][-1]
            source_plug = "{}.outMesh".format(cmds.listRelatives(last_node,
                                                                 s=True)[0])
            dest_plug = "{}.inMesh".format(cmds.listRelatives(driven_node,
                                                              s=True)[0])
            cmds.connectAttr(source_plug, dest_plug, f=True)
            direct_connect_dict[driver_render].append(driven_node)\
    # hide all recently created nodes
    [cmds.setAttr("{}.v".format(x), 0) for x in list(set(hide_all_nodes))]


def create_rigid_nodes_legacy(rigid_nodes, nucleus_node):
    """create the connections with the passive geometry and the sim layers.
    This is treated differently due to the rigid/passive geo is not wrapped
    but directly connected. And it is not duplicated for every layer, just up
    to the sim layer.

    Args:
        rigid_nodes (list): of rigid/passive nodes to connect to nucleus
        nucleus_node (str): nucleus node to connect to
    """
    connection_order = []
    # the sim layer is the middle portion of the layers, this could be
    # configured differently
    sim_index = CONFIG["grouping_order"].index(CONFIG["sim_layer"])
    # only duplicating up to the disired sim layer
    for rNode in rigid_nodes:
        for layer in CONFIG["grouping_order"][:sim_index + 1]:
            rigid_node = "{}_{}".format(rNode, layer)
            if layer == CONFIG["sim_layer"]:
                rigid_node = "{}_{}{}{}".format(rNode,
                                                layer,
                                                CONFIG["rigid_suffix"],
                                                CONFIG["nCloth_output_suffix"])
            rigid_node = cmds.duplicate(rNode,
                                        n=removeNS(rigid_node),
                                        un=False)[0]
            freeze_verticies(rigid_node)
            # adding the source geo to start the connections
            if rNode not in connection_order:
                connection_order.append(rNode)
            connection_order.append(rigid_node)
            cmds.parent(rigid_node, layer)
            locknHide(rigid_node)
            # on source layer, make it a rigid object
            if layer == CONFIG["sim_layer"]:
                cmds.select(cl=True)
                cmds.select(rigid_node, nucleus_node)
                rigid_shape = mel.eval("makeCollideNCloth;")[0]
                rigid_trans = cmds.listRelatives(rigid_shape, p=True)[0]
                rigid_name = rigid_node.replace(CONFIG["nCloth_output_suffix"],
                                                "")
                rigid_trans = cmds.rename(rigid_trans, rigid_name)
                cmds.parent(rigid_trans, layer)
                locknHide(rigid_trans)

    # create all the connections with the collected info
    for rigid_layers in chunks(connection_order[1:], sim_index + 2):
        for index, node in enumerate(rigid_layers):
            source_plug = "{}.outMesh".format(cmds.listRelatives(node, s=True)[0])
            next_val = index + 1
            if next_val > len(rigid_layers) - 1:
                break
            dest_plug = "{}.inMesh".format(cmds.listRelatives(rigid_layers[next_val], s=True)[0])
            cmds.connectAttr(source_plug, dest_plug, f=True)


def create_output_layer(techanim_info, falloffMode=1, exclusiveBind=1, **kwargs):
    """Convenience function to create the output layer

    Args:
        techanim_info (dict): render: sim cage
        falloffMode (int, optional): 1: volume, 0: surface
        exclusiveBind (int, optional): 0: off, 1: on
    """
    inv_dict = {v: k for k, v in techanim_info.iteritems()}
    populate_connection_layer(inv_dict,
                              CONFIG["output_suffix"],
                              CONFIG["sim_output"],
                              CONFIG["render_output"],
                              wrap=True,
                              falloffMode=falloffMode,
                              exclusiveBind=exclusiveBind)


def populate_connection_layer(techanim_info,
                              suffix,
                              groupA,
                              groupB,
                              wrap=True,
                              falloffMode=1,
                              exclusiveBind=1):
    """create the input layer that wraps the sim nodes to the render nodes
    to transfer performance for simulation.

    Args:
        techanim_info (dict): render_node:sim_node dict of names
        suffix (str): _something
        groupA (str): name to parent render nodes
        groupB (str): name to parent sim nodes to
        wrap (bool, optional): create a wrap between the keys:value
    """

    for driverR_node, driveN_node in techanim_info.iteritems():
        input_driveR_node = "{}{}".format(driverR_node, suffix)
        input_driveR_node = cmds.duplicate(driverR_node,
                                           n=removeNS(input_driveR_node),
                                           un=False,
                                           ic=False)[0]
        freeze_verticies(input_driveR_node)
        cmds.parent(input_driveR_node, groupA)
        locknHide(input_driveR_node)

        input_driveN_node = "{}{}".format(driveN_node, suffix)
        input_driveN_node = cmds.duplicate(driveN_node,
                                           n=removeNS(input_driveN_node),
                                           un=False,
                                           ic=False)[0]
        freeze_verticies(input_driveN_node)
        cmds.parent(input_driveN_node, groupB)
        locknHide(input_driveN_node)
        if wrap:
            wrapDeformer = create_wrap(input_driveR_node,
                                       input_driveN_node,
                                       exclusiveBind=exclusiveBind,
                                       falloffMode=falloffMode)
            cmds.rename(wrapDeformer, "{}_wrap".format(input_driveR_node))
            cmds.select(cl=True)


def freeze_verticies(nodes):
    """Applying a cluster to nodes freezes cv's on a shape

    Args:
        nodes (list, str): nodes to apply cluster to
    """
    cluster = cmds.cluster(nodes)
    cmds.delete(cluster)


def populate_layer(techanim_info, group, suffix):
    """duplicate the source nodes into the desired group with the correct names

    Args:
        techanim_info (dict): render:sim nodes association
        group (str): name of group to parent sim nodes to
        suffix (str): _something
    """
    for render_node, sim_node in techanim_info.iteritems():
        node = "{}{}".format(sim_node, suffix)
        node = cmds.duplicate(sim_node,
                              n=removeNS(node),
                              un=False,
                              ic=False)[0]
        freeze_verticies(node)
        cmds.delete(node, ch=True)
        cmds.parent(node, group)
        cmds.setAttr("{}.v".format(node), 0)
        locknHide(node)


def update_additional_driven_info(added_driven_nodes_info):
    """Add render geo to the existing techanim setup with provided info

    Args:
        added_driven_nodes_info (dict): driver_geo: [driven_render_geo]
    """
    techanim_node_info = get_info(CONFIG["techanim_root"],
                                  CONFIG["nodes_attr"])
    add_info = techanim_node_info.get(ADDITIONAL_RENDER_OUTPUT_KEY, {})

    for driver, driven_node_options in added_driven_nodes_info.iteritems():
        added = []
        if driver in add_info:
            for driven in driven_node_options:
                for index, existing_driven in enumerate(add_info[driver]):
                    if driven[0] == existing_driven[0]:
                        add_info[driver][index] = driven
                        added.append(driven[0])

            for driven in driven_node_options:
                if driven[0] not in added:
                    add_info[driver].append(driven)
        else:
            add_info[driver] = driven_node_options

    techanim_node_info[ADDITIONAL_RENDER_OUTPUT_KEY] = add_info
    # set the info on the techanim node
    set_info(CONFIG["techanim_root"],
             CONFIG["nodes_attr"],
             techanim_node_info)


@create_chunk
def add_driven_render_nodes(driver, driven, exclusiveBind=1, falloffMode=1):
    """add nodes to the setup of the driver. This allows a sim node to
    drive (via a wrap) multiple render nodes

    Args:
        driver (str): of driver
        driven (list): of nodes to be duplicated, parents, driven
        exclusiveBind (int, optional): wrap settings
        falloffMode (int, optional): wrap settings
    """
    driven_node_options = []
    for render_node in driven:
        driven_node_options.append([render_node, exclusiveBind, falloffMode])
        dup_node_name = "{}{}".format(render_node, CONFIG["output_suffix"])
        dup_node = cmds.duplicate(render_node,
                                  n=removeNS(dup_node_name),
                                  un=False)[0]
        cmds.parent(dup_node, CONFIG["render_output"])
        freeze_verticies(dup_node)
        cmds.delete(dup_node, ch=True)
        locknHide(dup_node)

        cmds.select(cl=True)
        wrapDeformer = create_wrap(driver,
                                   dup_node,
                                   exclusiveBind=exclusiveBind,
                                   falloffMode=falloffMode)
        cmds.rename(wrapDeformer, "{}_wrap".format(dup_node))
        cmds.select(cl=True)
    added_driven_nodes_info = {}
    added_driven_nodes_info[driver] = driven_node_options
    update_additional_driven_info(added_driven_nodes_info)
    return added_driven_nodes_info


def create_layer_connections(techanim_info):
    """Connect the .outMesh to the .inMesh of the sim geo on the subsequent
    layer.

    Args:
        techanim_info (dict): render_geo: sim_geo, 1-1 association
    """
    for index, layer in enumerate(CONFIG["grouping_order"]):
        for render_node, sim_node in techanim_info.iteritems():
            source_node = "{}_{}".format(removeNS(sim_node), layer)
            next_val = index + 1
            if next_val > len(CONFIG["grouping_order"]) - 1:
                break
            dest_node = "{}_{}".format(removeNS(sim_node),
                                       CONFIG["grouping_order"][next_val])
            cmds.connectAttr("{}.outMesh".format(source_node),
                             "{}.inMesh".format(dest_node),
                             force=True)


def create_ncloth_setup():
    """create the ncloth setup on the sim layer, organize and rename the
    generated nodes. TODO: Does maya not have python commands for this?

    Returns:
        list: of the created nCloth nodes
    """
    sim_group = "{}_{}".format(CONFIG["sim_base_name"], CONFIG["sim_layer"])
    sim_geo = cmds.listRelatives(sim_group)
    cmds.select(cl=True)
    cmds.select(sim_geo)
    nCloth_shapes = mel.eval("createNCloth 1;")
    for nShape in nCloth_shapes:
        sim_mesh = cmds.listConnections("{}.inputMesh".format(nShape))[0]
        nShape = cmds.rename(nShape, "{}{}Shape".format(sim_mesh,
                                                        CONFIG["nCloth_suffix"]))
        nTrans = cmds.listRelatives(nShape, p=True)[0]
        nTrans = cmds.rename(nTrans, "{}{}".format(sim_mesh,
                                                   CONFIG["nCloth_suffix"]))

        cloth_trans = cmds.listConnections("{}.outputMesh".format(nShape))
        cloth_name = "{}{}{}".format(sim_mesh,
                                     CONFIG["nCloth_suffix"],
                                     CONFIG["nCloth_output_suffix"])
        cloth_name_shape = "{}{}{}Shape".format(sim_mesh,
                                                CONFIG["nCloth_suffix"],
                                                CONFIG["nCloth_output_suffix"])

        cloth_trans = cmds.rename(cloth_trans, cloth_name, ignoreShape=False)
        locknHide(cloth_trans)
        cloth_shape = cmds.listRelatives(cloth_trans, s=True)[0]
        cloth_shape = cmds.rename(cloth_shape,
                                  cloth_name_shape,
                                  ignoreShape=False)

        next_layer_mesh = sim_mesh.replace(CONFIG["sim_layer"],
                                           CONFIG["post_layer"])
        cmds.connectAttr("{}.outMesh".format(cloth_shape),
                         "{}.inMesh".format(next_layer_mesh),
                         f=True)

        cmds.parent([nTrans, cloth_trans],
                    cmds.listRelatives(sim_mesh, p=True)[0])

    nucleus_node = cmds.listConnections(nShape, type="nucleus")[0]
    nucleus_node = cmds.rename(nucleus_node, CONFIG["nucleus_name"])
    cmds.parent(nucleus_node, CONFIG["sim_layer"])

    return nucleus_node


def activate_ncloth_maps():
    """Maya sometimes wont register the ability to paint nmaps without first
    simulating them.
    """
    all_ncloth_objects = get_all_nCloth_nodes()
    for nNode in all_ncloth_objects:
        cmds.setAttr("{}.isDynamic".format(nNode, 1))

    for nuc in cmds.ls(type="nucleus"):
        cmds.setAttr("{}.enable".format(nuc), 1)
        cmds.setAttr("{}.startFrame".format(nuc), 1)

    [cmds.currentTime(x, e=True, u=True) for x in xrange(1, 4, 1)]
    cmds.currentTime(1)


def set_default_shader():
    """Set default shader on techanim setup
    """
    cmds.select(cl=True)
    cmds.select(cmds.listRelatives(CONFIG["techanim_root"],
                                   ad=True,
                                   type="mesh"))
    mel.eval('createAndAssignShader lambert "";')


@viewport_off
@create_chunk
def create_setup(techanim_info, setup_options=None):
    """create the entire default setup

    Args:
        techanim_info (dict): render_geo: sim_geo, 1-1 association
    """
    if not setup_options:
        setup_options = DEFAULT_SETUP_OPTIONS
    techanim_info = copy.deepcopy(techanim_info)
    create_techanim_grouping()
    rigid_nodes = techanim_info.get(RIGID_KEY, {})

    create_input_layer(techanim_info[RENDER_SIM_KEY], **setup_options)
    sim_layers = CONFIG["grouping_order"][1:-1]
    for layer in sim_layers:
        group = "{}_{}".format(CONFIG["sim_base_name"], layer)
        suffix = "_{}".format(layer)
        populate_layer(techanim_info[RENDER_SIM_KEY], group, suffix)

    create_output_layer(techanim_info[RENDER_SIM_KEY], **setup_options)
    create_layer_connections(techanim_info[RENDER_SIM_KEY])
    nucleus_node = create_ncloth_setup()
    create_rigid_nodes_wrap(rigid_nodes, nucleus_node, **setup_options)

    input_info = {}
    for render_geo in techanim_info[RENDER_SIM_KEY].keys():
        input_info[render_geo] = "{}{}".format(removeNS(render_geo),
                                               CONFIG["input_suffix"])
    techanim_info[RENDER_INPUT_KEY] = input_info
    pprint.pprint(techanim_info)
    add_info = techanim_info.pop(ADDITIONAL_RENDER_OUTPUT_KEY, {})

    set_info(CONFIG["techanim_root"],
             CONFIG["nodes_attr"],
             techanim_info)

    set_info(CONFIG["techanim_root"], CONFIG_ATTR, CONFIG)

    # support for additional geo driven by wraps
    if add_info:
        for driver, driven_node_options in add_info.iteritems():
            for driven in driven_node_options:
                add_driven_render_nodes(driver,
                                        [driven[0]],
                                        exclusiveBind=driven[1],
                                        falloffMode=driven[2])

    set_default_shader()
    activate_ncloth_maps()
    # sets all the ncloth maps to default so the arrays are accurate
    # for importing/exporting
    set_all_maps_default()
    nClothMapsPaths = setup_options.get("nClothMapsPaths", [])
    # maps are not to be confused with textures, perhaps this
    # is an overloaded term
    if nClothMapsPaths:
        import_weights_from_files(nClothMapsPaths)

    postScriptPath = setup_options.get("postScriptPath", None)
    if postScriptPath and os.path.exists(postScriptPath):
        run_post_script(postScriptPath)


# compatibility ---------------------------------------------------------------
create_rigid_nodes = create_rigid_nodes_legacy
