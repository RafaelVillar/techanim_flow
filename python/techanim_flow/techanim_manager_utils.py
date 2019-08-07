# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import generators
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

# Standard
import os
import ast
import copy
import pprint
import tempfile
import platform
import subprocess
from functools import wraps

import maya.cmds as cmds
import maya.mel as mel

from techanim_flow import techanim_creator_utils
reload(techanim_creator_utils)

# =============================================================================
# constants
# =============================================================================
# convenience, it was annoying to type over again
CONFIG = techanim_creator_utils.CONFIG
# This allows the setup(s) to choose only one cache dir per maya session
CACHE_DIR_NAME = "techanim"

# =============================================================================
# general functions
# =============================================================================


def get_render_nodes(root_node, namespaces=False):
    render_info = techanim_creator_utils.get_info(root_node,
                                                  CONFIG["nodes_attr"])
    if namespaces:
        render_nodes = render_info.keys()
    else:
        print(render_info)
        render_nodes = [techanim_creator_utils.removeNS(x) for x in render_info["render_sim"].keys()]
    return render_nodes


def get_all_setups_roots():
    """Get all root nodes of techanim setups using an attr from config

    Returns:
        list: of all found transforms
    """
    ta_roots = cmds.ls("*.{}".format(CONFIG["config_attr"]), r=True, o=True)
    return ta_roots


def get_all_setups_nodes():
    """This returns instantiated Techanim_setups

    Returns:
        list: of TechAnim_Setup classes
    """
    ta_roots = get_all_setups_roots()
    ta_nodes = [TechAnim_Setup(x) for x in ta_roots]
    return ta_nodes


def get_all_namespaces():
    """Get all of the namespaces

    Returns:
        list: of maya namespaces
    """
    cmds.namespace(setNamespace=':')
    return cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True)


def get_all_target_namespaces():
    """best guess at getting namespaces that the user would be interested
    in connecting to.

    Returns:
        list: of filtered namespaces
    """
    setup_roots = get_all_setups_roots()
    techanim_ns = [x.split(":")[0] for x in setup_roots]
    namespaces = get_all_namespaces()
    filtered_ns = []
    for ns in namespaces:
        if ns in ["UI", "ui", "shared", "Shared"] + techanim_ns:
            continue
        filtered_ns.append(ns)
    return filtered_ns


def get_added_dicts(a, b):
    """Add two dictionaries together, return new dictionary.
    if key in B already exists in A, do not override. None destructive.

    Args:
        a (dict): dictionary you want to ADD to
        b (dict): dict you want to add from, the new keys

    Returns:
        dict: copied from a, with b keys added
    """
    tmp = copy.deepcopy(a)
    for key, val in b.iteritems():
        if key not in tmp:
            tmp[key] = val
    return tmp


def get_temp_dir(root_dir, prefix="", suffix=""):
    """Use pythons built in tempfile to safely and quickly get a dir to save to

    Args:
        root_dir (str): root directory to start from
        suffix (str): to be added to the name of the made dir

    Returns:
        str: dirpath
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix,
                                suffix=suffix,
                                dir=os.path.abspath(root_dir))
    return temp_dir


def ensure_unique_cache_dir(cache_dir, suffix=""):
    parent_dir = os.path.basename(os.path.abspath(os.path.join(cache_dir, os.pardir)))
    dir_name = os.path.basename(cache_dir)
    if dir_name == CACHE_DIR_NAME:
        # create the tmp folder and set on config
        cache_dir = get_temp_dir(cache_dir,
                                 suffix=suffix)
    elif dir_name.endswith("_techanim") and parent_dir == CACHE_DIR_NAME:
        pass
    else:
        # root dir from config create techanim cache root
        potential_path = os.path.join(cache_dir, CACHE_DIR_NAME)
        # if the provided cache dir does not end in techanim and one does not
        # exist, create one
        if (os.path.basename(cache_dir) != CACHE_DIR_NAME and not
                os.path.exists(potential_path)):
            os.makedirs(potential_path)
            cache_dir = potential_path
            cache_dir = get_temp_dir(cache_dir,
                                     suffix=suffix)

    return os.path.abspath(cache_dir)


def open_folder(path):
    """https://stackoverflow.com/questions/6631299/python-opening-a-folder-in-explorer-nautilus-mac-thingie

    Args:
        path (TYPE): Description
    """
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class TechAnim_Setup(object):

    """Convencience functionality to manager a techanim setup for simulations

    Attributes:
        input_layer (str): of the input layer top node
        nodes_to_hide (str): nodes not to display in the techanim_managerUI
        output_layer (str): name of the output layer topnode
        root_node (str): root to this setup
        setup_config (dict): a config that was pulled from an attr on setup
        sim_layers (list): of the 'sim' top nodes, pre, sim, post
        suffixes_to_hide (list): nodes with suffix wont be shown in the ui
        target_namespace (str): desired namespace of a rig or alembin to
        attach to
        techanim_info (dict): of useful information for the UI or user to interact with
        techanim_ns (str): namespace of this setup
    """

    def __init__(self, root_node, target_namespace=None):
        super(TechAnim_Setup, self).__init__()
        self.root_node = root_node
        self.techanim_info = {}
        self.setup_config = {}
        self.nodes_to_hide = []
        self.suffixes_to_hide = []
        self.potentionally_faulty_connections = {}
        self.set_config()

        if ":" in self.root_node:
            self.techanim_ns = "{}:".format(self.root_node.partition(":")[0])
        else:
            self.techanim_ns = ""

        # self.sim_layer = self._wrap_ns(self.setup_config["sim_layer"])
        sim_layers = self.setup_config["grouping_order"][1:-1]
        self.sim_layers = [self._wrap_ns(x) for x in sim_layers]
        self.input_layer = self._wrap_ns(self.setup_config["grouping_order"][0])
        self.output_layer = self._wrap_ns(self.setup_config["grouping_order"][-1])

        if not target_namespace:
            target_namespace = self.get_target_namespace()
        self.set_target_namespace(target_namespace)
        self.refresh_info()

    def __str__(self):
        """so it prints the name of the node

        Returns:
            str: name of the node
        """
        return self.root_node

    def __repr__(self):
        """So it can print the name of the node

        Returns:
            str: name of root node
        """
        return self.root_node

    def set_target_namespace(self, namespace):
        """when the target namespace is set, make any changes or prep

        Args:
            namespace (str): of the target ns
        """
        # do shit
        self.target_namespace = namespace.strip(":")

    @property
    def print_faulty_connections(self):
        """Summary
        """
        print("The following failed connections could be intentional.")
        pprint.pprint(self.potentionally_faulty_connections)

    def _wrap_ns(self, node):
        """convenience function, wrap any node belonging to this setup in the
        namespace retrieved when initialized

        Args:
            node (str): node in setup to be wrapped with ns

        Returns:
            str: wrapped shit
        """
        return "{}{}".format(self.techanim_ns, node)

    @property
    def is_setup_referenced(self):
        return cmds.referenceQuery(self.root_node, inr=True)

    def import_setup(self):
        if self.is_setup_referenced:
            ref_node = cmds.referenceQuery(self.root_node, rfn=True)
            ref_file = cmds.referenceQuery(ref_node, f=True)
            cmds.file(ref_file, ir=True)

    def get_cache_dir(self, prefix="", suffix=""):
        """get the cache dir that will be used during the creation of any new
        caches

        Returns:
            str: should be good on any os
        """
        cache_dir = self.setup_config.get("cache_dir")
        suffix = self.setup_config["cache_dir_suffix"]
        unique_cache_dir = ensure_unique_cache_dir(cache_dir, suffix=suffix)
        if unique_cache_dir != cache_dir:
            self.update_cache_dir(cache_dir)
        return cache_dir

    def set_setup_config_info(self, data):
        """Overwrite the entirety of the current setup config with the
        provided data.

        Args:
            data (dict): new config information
        """
        techanim_creator_utils.set_info(self.root_node,
                                        techanim_creator_utils.CONFIG_ATTR,
                                        data)

    def update_config_key(self, key, data):
        """Update an entry in the current config. Existing or not.

        Args:
            key (str): name of the key, entry
            data (str, bool, list): new information that will be cast as str
        """
        self.setup_config[key] = data
        techanim_creator_utils.set_info(self.root_node,
                                        techanim_creator_utils.CONFIG_ATTR,
                                        self.setup_config)

    def update_cache_dir(self, new_dir):
        suffix = self.setup_config["cache_dir_suffix"]
        cache_dir = ensure_unique_cache_dir(new_dir, suffix=suffix)
        self.update_config_key("cache_dir", cache_dir)
        msg = "{} >> {}".format(self.setup_config["cache_dir"],
                                cache_dir)
        print("Cache directory updated!")
        print(msg)

    def __toggle_nuclei(func):
        """Disable the nuclui in the setup for the current fucntion

        Args:
            func (function): function to disable nukes during run
        """
        @wraps(func)
        def run_disabled_nuclei(self, *args, **kwargs):
            self.toggle_nuclei(value=0)
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                print(e)
            finally:
                self.toggle_nuclei(value=1)

        return run_disabled_nuclei

    def toggle_view(func):
        """
        """
        @wraps(func)
        def turn_off_display(self, *args, **kwargs):
            gMainPane = mel.eval('global string $gMainPane; $temp = $gMainPane;')
            cmds.paneLayout(gMainPane, edit=True, manage=False)
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                print(e)
            finally:
                cmds.paneLayout(gMainPane, edit=True, manage=True)

        return turn_off_display

    def set_config(self):
        """set config on this setup. Decide if it will merge with stored, or
        follow env variable one. TODO
        """
        str_config = cmds.getAttr("{}.{}".format(self.root_node,
                                                 CONFIG["config_attr"]))
        try:
            # THIS NEEDS TO BE REVISTED. I am adding shit from file
            stored_config = ast.literal_eval(str_config)
            self.setup_config = get_added_dicts(stored_config, CONFIG)
            techanim_creator_utils.set_info(self.root_node,
                                            techanim_creator_utils.CONFIG_ATTR,
                                            self.setup_config)
        except Exception:
            cmds.warning("Could not retrieve CONFIG stored on setup!")
            self.setup_config = CONFIG

    def refresh_info(self):
        """refresh the info dict on setup with all new information

        Returns:
            dict: of new information
        """
        if not self.is_setup_connected() and not self.target_namespace:
            return
        self.get_association_info()
        self.create_techanim_connections()

    def get_layer_nodes_info(self, desired_layers):
        """return a dictionary of the topnode_name: [children of node]

        Args:
            desired_layers (list): of nodes to query

        Returns:
            dict: {node: [list of all children]}
        """
        techanim_nodes_info = {}
        for layer in desired_layers:
            techanim_nodes_info[layer] = cmds.listRelatives(layer,
                                                            ad=True,
                                                            type="transform")
        return techanim_nodes_info

    def is_setup_connected(self):
        """searches all the output nodes to see if they are connected
        to anything, they should only every be connected to target animation

        Returns:
            bool: True False
        """
        return bool(self.get_target_namespace())

    def get_target_namespace(self):
        """Best guess based on connections for the target ns

        Returns:
            str: empty string or target
        """
        output_group = self._wrap_ns(self.setup_config["render_output"])
        namespace = ""
        for output_node in cmds.listRelatives(output_group):
            output_node_plug = "{}.outMesh".format(output_node)
            render_node = cmds.listConnections(output_node_plug)
            if not render_node:
                continue
            if ":" in render_node[0]:
                namespace = render_node[0].rpartition(":")[0]
                break

        return namespace

    def get_nuclei(self):
        """Nuclei, get them shits. Belonging to this setup.

        Returns:
            list: of found nuclei
        """
        sim_layer = self._wrap_ns(self.setup_config["sim_layer"])
        return cmds.listRelatives(sim_layer, ad=True, type="nucleus") or []

    def toggle_nuclei(self, nuclei=None, value=0):
        if not nuclei:
            nuclei = self.get_nuclei()
        for nuke in nuclei:
            cmds.setAttr("{}.enable".format(nuke), value)

    def set_start_nuclei_frame(self, start_frame, nucleus_nodes=None):
        """set the start from of all nucleus nodes in this setup

        Args:
            start_frame (int): start frame
            nucleus_nodes (list, optional): if not provided, will auto search
        """
        if not nucleus_nodes:
            nucleus_nodes = self.get_nuclei()
        for nuc in nucleus_nodes:
            cmds.setAttr("{}.startFrame".format(nuc), start_frame)

    def get_association_info(self):
        """after target ns set, put all the information together that the
        ui/user will need
        """
        str_nodes = cmds.getAttr("{}.{}".format(self.root_node,
                                                CONFIG["nodes_attr"]))
        temp_info = ast.literal_eval(str_nodes)

        self.techanim_info = {}
        rigid_info = {}
        for render_node in temp_info[techanim_creator_utils.RIGID_KEY]:
            render_node = "{}:{}".format(self.target_namespace,
                                         techanim_creator_utils.removeNS(render_node))
            input_node = "{}{}{}".format(self.techanim_ns,
                                         techanim_creator_utils.removeNS(render_node),
                                         self.setup_config["input_suffix"])
            rigid_info[render_node] = input_node
        self.techanim_info[techanim_creator_utils.RIGID_KEY] = rigid_info

        input_info = {}
        tmp_iter = temp_info[techanim_creator_utils.RENDER_INPUT_KEY].iteritems()
        for render_node, input_node in tmp_iter:
            render_node = "{}:{}".format(self.target_namespace,
                                         techanim_creator_utils.removeNS(render_node))
            input_node = "{}{}".format(self.techanim_ns,
                                       techanim_creator_utils.removeNS(input_node))
            input_info[render_node] = input_node

        self.techanim_info[techanim_creator_utils.RENDER_INPUT_KEY] = input_info

        for node in self.setup_config["nodes_to_hide"]:
            self.nodes_to_hide.append("{}{}".format(self.techanim_ns, node))

        self.suffixes_to_hide = self.setup_config["suffixes_to_hide"]

    def _create_input_layer_connections(self, input_info):
        for source, destination in input_info.iteritems():
            source_deformer = cmds.listConnections("{}.inMesh".format(source),
                                                   plugs=True)
            if source_deformer:
                # cycle fix, this was fun.
                if (source_deformer[0].rpartition(".")[0]
                        in cmds.listRelatives(self.root_node, ad=True)):
                    continue
                dest_plug = "{}.inMesh".format(destination)
                if cmds.isConnected(source_deformer[0], dest_plug):
                    continue
                cmds.connectAttr(source_deformer[0], dest_plug, f=True)

    def create_techanim_connections(self):
        """We are connecting the techanim to the rig on every initialization,
        check into this later to see if this is best practice or not.
        """
        self.import_setup()
        input_info = self.techanim_info[techanim_creator_utils.RENDER_INPUT_KEY]
        self._create_input_layer_connections(input_info)
        rigid_info = self.techanim_info[techanim_creator_utils.RIGID_KEY]
        self._create_input_layer_connections(rigid_info)

        # output connections to the rig/alembic
        layers = [self._wrap_ns(self.setup_config["render_output"])]
        render_output_nodes = self.get_layer_nodes_info(layers)
        for layer, output_nodes in render_output_nodes.iteritems():
            for oNode in output_nodes:
                src_plug = "{}.outMesh".format(oNode)
                render_node = oNode.rpartition(self.setup_config["output_suffix"])[0]
                render_node = techanim_creator_utils.removeNS(render_node)
                render_node = "{}:{}".format(self.target_namespace,
                                             render_node)
                dest_plug = "{}.inMesh".format(render_node)
                # test if already connected so we do not get the warnings
                if not cmds.isConnected(src_plug, dest_plug):
                    try:
                        cmds.connectAttr(src_plug, dest_plug, f=True)
                    except Exception as e:
                        plug_str = "{} >> {}".format(src_plug, dest_plug)
                        msg = str(e)
                        self.potentionally_faulty_connections[plug_str] = msg
        if self.potentionally_faulty_connections:
            self.print_faulty_connections()

    def show_nodes(self, nodes, select_second=None, isolate=False, select=False):
        """Displays the desired nodes and any parent nodes that may be hidden

        Args:
            nodes (list): of desired nodes
            isolate (bool, optional): isolate in viewport
            select (bool, optional): should desired nodes be selected as well
        """
        cmds.hide(cmds.listRelatives(self.root_node,
                                     ad=True,
                                     type="transform"))
        cmds.showHidden(nodes, a=True)

        if select or isolate:
            cmds.select(nodes)
            if select_second:
                cmds.select(select_second, add=True)

        if isolate:
            isolated_panel = cmds.paneLayout('viewPanes', q=True, pane1=True)
            cmds.isolateSelect(isolated_panel, state=True)
            cmds.isolateSelect(isolated_panel, aso=True)

    @toggle_view
    @__toggle_nuclei
    def cache_input_layer(self, start_frame, end_frame, cache_dir=None):
        """Using mel to create the caches on the input later nodes

        Args:
            start_frame (int): start frame
            end_frame (int): end frame
            cache_dir (str, optional): path to desired dir, or will auto search
        """
        # Description:
        # Create cache files on disk for the selected shape(s) according
        # to the specified flags described below.

        # $version == 1:
        # $args[0] = time range mode:
        # time range mode = 0 : use $args[1] and $args[2] as start-end
        # time range mode = 1 : use render globals
        # time range mode = 2 : use timeline
        # $args[1] = start frame (if time range mode == 0)
        # $args[2] = end frame (if time range mode == 0)

        # $version == 2:
        # $args[3] = cache file distribution, either "OneFile" or "OneFilePerFrame"
        # $args[4] = 0/1, whether to refresh during caching
        # $args[5] = directory for cache files, if "", then use project data dir
        # $args[6] = 0/1, whether to create a cache per geometry
        # $args[7] = name of cache file. An empty string can be used to specify that an auto-generated name is acceptable.
        # $args[8] = 0/1, whether the specified cache name is to be used as a prefix
        # $version == 3:
        # $args[9] = action to perform: "add", "replace", "merge", "mergeDelete" or "export"
        # $args[10] = force save even if it overwrites existing files
        # $args[11] = simulation rate, the rate at which the cloth simulation is forced to run
        # $args[12] = sample mulitplier, the rate at which samples are written, as a multiple of simulation rate.

        # $version == 4:
        # $args[13] = 0/1, whether modifications should be inherited from the cache about to be replaced. Valid
        # only when $action == "replace".
        # $args[14] = 0/1, whether to store doubles as floats
        # $version == 5:
        # $args[15] = name of cache format
        # $version == 6:
        # $args[16] = 0/1, whether to export in local or world space
        #                            0    1     2       3       4    5  6   7  8     9     10   11   12  13  14   15   16
        # doCreateGeometryCache 6 { "2", "1", "10", "OneFile", "1", "","1","","0", "add", "0", "1", "1","0","1","mcx","0" } ;
        try:
            self.delete_input_layer_cache()
        except Exception:
            pass
        cache_cmd = 'doCreateGeometryCache 6 {{ "0", "{start_frame}", "{end_frame}", "OneFile", "1", "{cache_dir}", "1", "", "0", "replace", "1", "1", "1","0","1","mcx","{world_space}" }} ;'
        cache_arg_info = {
            "start_frame": start_frame,
            "end_frame": end_frame,
            "cache_dir": cache_dir or self.get_cache_dir().replace("\\", "/"),
            "world_space": 1
        }

        cache_cmd = cache_cmd.format(**cache_arg_info)
        input_shapes = cmds.listRelatives(self.input_layer, ad=True, type=["mesh"])
        shapes_to_cache = []
        for shape in input_shapes:
            if cmds.listConnections("{}.inMesh".format(shape)):
                shapes_to_cache.append(shape)
        cmds.select(cl=True)
        print("Caching: {}".format(shapes_to_cache))
        # Wow, it will not performa a geometry cache if the geo is hidden
        # fun bug, hours lost.
        cmds.showHidden(shapes_to_cache, above=True)
        cmds.select(shapes_to_cache)
        mel.eval(cache_cmd)

    def delete_sim_cache(self, nodes):
        """There is an annoying mel bug that if you run delete using mel
        it will still error even if wrapped. So we do a search before trying.

        Args:
            nodes (list): of nodes to delete caches on, they will be searched
        """
        cached_nodes = []

        cached_nodes = self.is_node_cached(nodes)
        if cached_nodes:
            cmds.select(cached_nodes)
            mel.eval('deleteCacheFile 2 { "keep", "" } ;')

    def delete_input_layer_cache(self):
        """delete input layer on any nodes
        """
        # deleteGeometryCache;
        # performDeleteGeometryCache 0;
        # deleteCacheFile 3 { "delete", "", "geometry" };
        input_nodes = self.get_layer_nodes_info([self.input_layer])
        cached_nodes = self.is_node_cached(input_nodes.values()[0])
        if cached_nodes:
            cmds.select(cached_nodes)
            try:
                mel.eval("performDeleteGeometryCache 0;")
                # mel.eval("performDeleteGeometryCache 0;")
            except Exception:
                pass

    def is_input_layer_cached(self):
        """does the input layer have any nodes with caches on them

        Returns:
            list: of nodes with caches on them
        """
        input_nodes = self.get_layer_nodes_info([self.input_layer])
        return self.is_node_cached(input_nodes.values()[0])

    def is_sim_layer_cached(self):
        """are there any nodes in the sim layer that have cache nodes on them

        Returns:
            list: of nodes with caches on them
        """
        layers = [self._wrap_ns(self.setup_config["sim_layer"])]
        input_nodes = self.get_layer_nodes_info(layers)
        return self.is_node_cached(input_nodes.values()[0])

    def is_node_cached(self, nodes):
        """are the specific nodes supplied cached in anyway

        Args:
            nodes (list): of nodes that may be cached

        Returns:
            list: of nodes containing cache nodes
        """
        nodes_with_cache = []
        for node in nodes:
            for shape in cmds.listRelatives(node, shapes=True) or []:
                if cmds.listConnections(shape, type="historySwitch"):
                    nodes_with_cache.extend([node, shape])
                elif cmds.listConnections(shape, type="cacheFile"):
                    nodes_with_cache.extend([node, shape])

        return nodes_with_cache

    @toggle_view
    def cache_sim_nodes(self, nodes, start_frame, end_frame, cache_dir=None):
        """More annoying mel shit, you cannot run a cache on a node
        that already has a cache on it without getting a UI pop up.

        Args:
            nodes (list): of nodes to cache
            start_frame (int): start frame
            end_frame (int): end frame
            cache_dir (str, optional): if none, will auto search
        """
        # Create cache files on disk for the select ncloth object(s) according
        # to the specified flags described below.

        # $version == 1:
        # $args[0] = time range mode:
        # time range mode = 0 : use $args[1] and $args[2] as start-end
        # time range mode = 1 : use render globals
        # time range mode = 2 : use timeline
        # $args[1] = start frame (if time range mode == 0)
        # $args[2] = end frame (if time range mode == 0)

        # $version == 2:
        # $args[3] = cache file distribution, either "OneFile" or "OneFilePerFrame"
        # $args[4] = 0/1, whether to refresh during caching
        # $args[5] = directory for cache files, if "", then use project data dir
        # $args[6] = 0/1, whether to create a cache per geometry
        # $args[7] = name of cache file. An empty string can be used to specify that an auto-generated name is acceptable.
        # $args[8] = 0/1, whether the specified cache name is to be used as a prefix
        # $version == 3:
        # $args[9] = action to perform: "add", "replace", "merge" or "mergeDelete"
        # $args[10] = force save even if it overwrites existing files
        # $args[11] = simulation rate, the rate at which the cloth simulation is forced to run
        # $args[12] = sample mulitplier, the rate at which samples are written, as a multiple of simulation rate.
        # $version == 4:
        # $args[13] = 0/1, whether modifications should be inherited from the cache about to be replaced.
        # $args[14] = 0/1, whether to store doubles as floats
        # $version == 5:
        # $args[15] = cache format type: mcc or mcx.
        #                          0    1     2       3       4    5  6   7  8     9     10   11   12  13  14   15
        # doCreateNclothCache 5 { "2", "1", "10", "OneFile", "1", "","0","","0", "add", "0", "1", "1","0","1","mcx" } ;
        cache_cmd = 'doCreateNclothCache 5 {{ "3", "{start_frame}", "{end_frame}", "OneFile", "1", "{cache_dir}", "1", "", "0", "replace", "0", "1", "1","0","1","mcx" }};'

        cache_arg_info = {
            "start_frame": start_frame,
            "end_frame": end_frame,
            "cache_dir": cache_dir or self.get_cache_dir().replace("\\", "/")
        }
        self.delete_sim_cache(nodes)
        cache_cmd = cache_cmd.format(**cache_arg_info)
        cmds.select(nodes)
        print(cache_cmd)
        mel.eval(cache_cmd)
