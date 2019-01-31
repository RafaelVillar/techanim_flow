# -*- coding: utf-8 -*-

# Standard
from __future__ import division
from __future__ import generators
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

# standard
import copy
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
LOCK_ATTRS = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"]
CONFIG_ATTR = "techanim_config"

# Default options that would be interacted with from the UI
DEFAULT_SETUP_OPTIONS = {"falloffMode": "surface",
                         "exclusiveBind": 1}

# =============================================================================
# utils
# =============================================================================


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
            print(e)

        finally:
            cmds.undoInfo(chunkName=chunk_name, closeChunk=True)

    return open_chunk


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
                falloffMode="surface"):

    cmds.optionVar(fv=["weightThreshold", weightThreshold])
    cmds.optionVar(iv=["limitWrapInfluence", limitWrapInfluence])
    cmds.optionVar(iv=["maxDistance", maxDistance])
    cmds.optionVar(iv=["wrapInflType", wrapInflType])
    cmds.optionVar(iv=["exclusiveBind", exclusiveBind])
    cmds.optionVar(iv=["autoWeightThreshold", autoWeightThreshold])
    cmds.optionVar(iv=["renderInfl", renderInfl])
    print("falloffMode", falloffMode)
    cmds.optionVar(sv=["falloffMode", falloffMode])

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
        cmds.addAttr(node, ln=attr, dt="string")
    except Exception:
        pass
    cmds.setAttr("{}.{}".format(node, attr), str(data), type="string")


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


def create_input_layer(techanim_info,
                       falloffMode=1,
                       exclusiveBind=1):
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


def create_rigid_nodes(rigid_nodes, nucleus_node):
    """create the connections with the passive geometry and the sim layers
    This is treated differently due to the rigid/passive geo is not wrapped
    but directly connected. And it is not duplicated for every layer, just up
    to the sim layer. It probably does not need to be connected to the input
    layer, but for consistency sake it is.

    Args:
        rigid_nodes (list): of rigid/passive nodes to connect to nucleus
        nucleus_node (str): nucleus node to connect to
    """
    connection_order = []
    # the sim layer is the middle portion of the layers, this could be
    # configured differently
    sim_index = CONFIG["grouping_order"].index(CONFIG["sim_layer"])
    # only duplicating up to the disired sim layer
    for layer in CONFIG["grouping_order"][:sim_index + 1]:
        for rNode in rigid_nodes:
            rigid_node = "{}_{}".format(rNode, layer)
            if layer == CONFIG["sim_layer"]:
                rigid_node = "{}_{}{}{}".format(rNode,
                                                layer,
                                                CONFIG["rigid_suffix"],
                                                CONFIG["nCloth_output_suffix"])
            rigid_node = cmds.duplicate(rNode,
                                        n=removeNS(rigid_node),
                                        un=False)[0]
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
                # rigid_name = "{}{}".format(rigid_name, CONFIG["rigid_suffix"])
                rigid_trans = cmds.rename(rigid_trans, rigid_name)
                cmds.parent(rigid_trans, layer)
                locknHide(rigid_trans)

    # create all the connections with the collected info
    for rigid_layers in chunks(connection_order[1:], sim_index + 2):
        for index, node in enumerate(rigid_layers):
            source_plug = "{}Shape.outMesh".format(node)
            next_val = index + 1
            if next_val > len(rigid_layers) - 1:
                break
            dest_plug = "{}Shape.inMesh".format(rigid_layers[next_val])
            cmds.connectAttr(source_plug, dest_plug, f=True)


def create_output_layer(techanim_info, falloffMode=1, exclusiveBind=1):
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
                                           un=False)[0]
        cmds.parent(input_driveR_node, groupA)
        locknHide(input_driveR_node)

        input_driveN_node = "{}{}".format(driveN_node, suffix)
        input_driveN_node = cmds.duplicate(driveN_node,
                                           n=removeNS(input_driveN_node),
                                           un=False)[0]
        cmds.parent(input_driveN_node, groupB)
        locknHide(input_driveN_node)
        if wrap:
            wrapDeformer = create_wrap(input_driveR_node,
                                       input_driveN_node,
                                       exclusiveBind=exclusiveBind,
                                       falloffMode=falloffMode)
            cmds.rename(wrapDeformer, "{}_wrap".format(input_driveR_node))
            cmds.select(cl=True)


def populate_layer(techanim_info, group, suffix):
    """duplicate the source nodes into the desired group with the correct names

    Args:
        techanim_info (dict): render:sim nodes association
        group (str): name of group to parent sim nodes to
        suffix (str): _something
    """
    for render_node, sim_node in techanim_info.iteritems():
        node = "{}{}".format(sim_node, suffix)
        node = cmds.duplicate(sim_node, n=removeNS(node), un=False)[0]
        cmds.delete(node, ch=True)
        cmds.parent(node, group)
        cmds.setAttr("{}.v".format(node), 0)
        locknHide(node)


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
    for render_node in driven:
        dup_node_name = "{}{}".format(render_node, CONFIG["output_suffix"])
        dup_node = cmds.duplicate(render_node,
                                  n=removeNS(dup_node_name),
                                  un=False)[0]
        cmds.parent(dup_node, CONFIG["render_output"])
        cmds.delete(dup_node, ch=True)
        locknHide(dup_node)

        cmds.select(cl=True)
        wrapDeformer = create_wrap(driver,
                                   dup_node,
                                   exclusiveBind=exclusiveBind,
                                   falloffMode=falloffMode)
        cmds.rename(wrapDeformer, "{}_wrap".format(dup_node))
        cmds.select(cl=True)


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
            # print(dest_node)
            cmds.connectAttr("{}.outMesh".format(source_node),
                             "{}.inMesh".format(dest_node),
                             force=True)


def create_ncloth_setup(rigid_nodes):
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
        # print(next_layer_mesh)
        cmds.connectAttr("{}.outMesh".format(cloth_shape),
                         "{}.inMesh".format(next_layer_mesh),
                         f=True)

        cmds.parent([nTrans, cloth_trans],
                    cmds.listRelatives(sim_mesh, p=True)[0])

    nucleus_node = cmds.listConnections(nShape, type="nucleus")[0]
    nucleus_node = cmds.rename(nucleus_node, CONFIG["nucleus_name"])
    cmds.parent(nucleus_node, CONFIG["sim_layer"])

    create_rigid_nodes(rigid_nodes, nucleus_node)

    return nCloth_shapes


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
    rigid_nodes = techanim_info.get(RIGID_KEY, [])

    create_input_layer(techanim_info[RENDER_SIM_KEY], **setup_options)

    sim_layers = CONFIG["grouping_order"][1:-1]
    for layer in sim_layers:
        group = "{}_{}".format(CONFIG["sim_base_name"], layer)
        suffix = "_{}".format(layer)
        populate_layer(techanim_info[RENDER_SIM_KEY], group, suffix)

    create_output_layer(techanim_info[RENDER_SIM_KEY], **setup_options)
    create_layer_connections(techanim_info[RENDER_SIM_KEY])
    create_ncloth_setup(rigid_nodes)

    input_info = {}
    for render_geo in techanim_info[RENDER_SIM_KEY].keys():
        input_info[render_geo] = "{}{}".format(render_geo,
                                               CONFIG["input_suffix"])
    techanim_info[RENDER_INPUT_KEY] = input_info

    print(techanim_info)
    set_info(CONFIG["techanim_root"],
             CONFIG["nodes_attr"],
             techanim_info)

    set_info(CONFIG["techanim_root"], CONFIG_ATTR, CONFIG)

    cmds.select(CONFIG["techanim_root"])
