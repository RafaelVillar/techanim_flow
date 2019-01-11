# -*- coding: utf-8 -*-
# Standard
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import generators
from __future__ import division

import ast

import maya.cmds as cmds
import maya.mel as mel

import creator_utils
reload(creator_utils)
from creator_utils import CONFIG


def get_all_setups_roots():
    ta_roots = cmds.ls("*.{}".format(CONFIG["config_attr"]), r=True, o=True)
    return ta_roots


def get_all_setups_nodes():
    ta_roots = get_all_setups_roots()
    ta_nodes = [TechAnim_Setup(x) for x in ta_roots]
    return ta_nodes


def get_all_namespaces():
    cmds.namespace(setNamespace=':')
    return cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True)


class TechAnim_Setup(object):
    """docstring for TechAnim_Setup"""
    def __init__(self, root_node, target_namespace=None):
        super(TechAnim_Setup, self).__init__()
        self.root_node = root_node
        self.techanim_info = {}
        self.setup_config = {}
        self.set_config()

        if ":" in self.root_node:
            self.techanim_ns = "{}:".format(self.root_node.partition(":")[0])
        else:
            self.techanim_ns = ""

        sim_layers = self.setup_config["grouping_order"][1:-1]
        self.sim_layers = ["{}{}".format(self.techanim_ns, x)
                           for x in sim_layers]
        self.input_layer = "{}{}".format(self.techanim_ns,
                                         self.setup_config["grouping_order"][0])
        self.output_layer = "{}{}".format(self.techanim_ns,
                                          self.setup_config["grouping_order"][-1])

        if not target_namespace:
            target_namespace = self.get_target_namespace()
        self.set_target_namespace(target_namespace)
        self.refresh_info()

    def __str__(self):
        return self.root_node

    def __repr__(self):
        return self.root_node

    def set_target_namespace(self, namespace):
        # do shit
        self.target_namespace = namespace.strip(":")

    def set_config(self):
        str_config = cmds.getAttr("{}.{}".format(self.root_node,
                                                 CONFIG["config_attr"]))
        try:
            self.setup_config = ast.literal_eval(str_config)
        except Exception:
            self.setup_config = CONFIG

    def refresh_info(self):
        if not self.is_setup_connected() and not self.target_namespace:
            return
        self.get_association_info()
        self.create_techanim_connections()

    def get_layer_nodes_info(self, desired_layers):
        techanim_nodes_info = {}
        for layer in desired_layers:
            techanim_nodes_info[layer] = cmds.listRelatives(layer,
                                                            ad=True,
                                                            type="transform")
        return techanim_nodes_info

    def is_setup_connected(self):
        return bool(self.get_target_namespace())

    def get_target_namespace(self):
        output_group = "{}{}".format(self.techanim_ns,
                                     self.setup_config["render_output"])
        namespace = None
        for output_node in cmds.listRelatives(output_group):
            output_node_plug = "{}.outMesh".format(output_node)
            render_node = cmds.listConnections(output_node_plug)
            if not render_node:
                continue
            if ":" in render_node[0]:
                namespace = render_node[0].rpartition(":")[0]
                break

        return namespace

    def get_association_info(self):
        str_nodes = cmds.getAttr("{}.{}".format(self.root_node,
                                                CONFIG["nodes_attr"]))
        temp_info = ast.literal_eval(str_nodes)

        self.techanim_info = {}
        rigid_key = creator_utils.RIGID_KEY
        rigid_nodes = ["{}:{}".format(self.target_namespace,
                                      creator_utils.removeNS(node)) for node in temp_info[rigid_key]]
        self.techanim_info[rigid_key] = rigid_nodes
        input_info = {}
        tmp_iter = temp_info[creator_utils.RENDER_INPUT_KEY].iteritems()
        for render_node, input_node in tmp_iter:
            render_node = "{}:{}".format(self.target_namespace,
                                         creator_utils.removeNS(render_node))
            input_node = "{}{}".format(self.techanim_ns, creator_utils.removeNS(input_node))
            input_info[render_node] = input_node

        self.techanim_info[creator_utils.RENDER_INPUT_KEY] = input_info

    def create_techanim_connections(self):
        """We are connecting the techanim to the rig on every initialization,
        check into this later to see if this is best practice or not.
        """
        input_info = self.techanim_info[creator_utils.RENDER_INPUT_KEY]
        for source, destination in input_info.iteritems():
            source_deformer = cmds.listConnections("{}.inMesh".format(source),
                                                   plugs=True)
            if source_deformer:
                # cycle fix, this was fun.
                if (source_deformer[0].rpartition(".")[0]
                        in cmds.listRelatives(self.root_node, ad=True)):
                    continue
                cmds.connectAttr(source_deformer[0],
                                 "{}.inMesh".format(destination),
                                 f=True)

        layers = ["{}{}".format(self.techanim_ns,
                                self.setup_config["render_output"])]
        render_output_nodes = self.get_layer_nodes_info(layers)
        for layer, output_nodes in render_output_nodes.iteritems():
            for oNode in output_nodes:
                src_plug = "{}.outMesh".format(oNode)
                render_node = oNode.rpartition(self.setup_config["output_suffix"])[0]
                render_node = creator_utils.removeNS(render_node)
                render_node = "{}:{}".format(self.target_namespace, render_node)
                dest_plug = "{}.inMesh".format(render_node)
                # test if already connected so we do not get the warnings
                if not cmds.isConnected(src_plug, dest_plug):
                    cmds.connectAttr(src_plug, dest_plug, f=True)

    def show_nodes(self, nodes, isolate=False, select=False):
        cmds.hide(cmds.listRelatives(self.root_node,
                                     ad=True,
                                     type="transform"))
        cmds.showHidden(nodes, a=True)

        if select or isolate:
            cmds.select(nodes)

        if isolate:
            isolated_panel = cmds.paneLayout('viewPanes', q=True, pane1=True)
            cmds.isolateSelect(isolated_panel, state=True)
            cmds.isolateSelect(isolated_panel, aso=True)

    def cache_input_layer(self, start_frame, end_frame):
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

        cache_cmd = 'doCreateGeometryCache 6 {{ "0", "{start_frame}", "{end_frame}", "OneFile", "1", "{cache_dir}", "1", "", "0", "replace", "1", "1", "1","0","1","mcx","{world_space}" }} ;'
        cache_arg_info = {
            "start_frame": start_frame,
            "end_frame": end_frame,
            "cache_dir": self.setup_config["cache_dir"],
            "world_space": 1
        }

        cache_cmd = cache_cmd.format(**cache_arg_info)
        input_nodes = self.get_layer_nodes_info([self.input_layer])
        cmds.select(input_nodes.values()[0])
        mel.eval(cache_cmd)

    def delete_input_layer_cache(self):
        # deleteGeometryCache;
        # performDeleteGeometryCache 0;
        # deleteCacheFile 3 { "delete", "", "geometry" };
        input_nodes = self.get_layer_nodes_info([self.input_layer])
        cmds.select(input_nodes.values()[0])
        try:
            mel.eval("performDeleteGeometryCache 0;")
        except Exception:
            pass

    def is_input_layer_cache(self):
        input_nodes = self.get_layer_nodes_info([self.input_layer])
        return self.is_node_cache(input_nodes.values()[0])

    def is_sim_layer_cache(self):
        layers = ["{}{}".format(self.techanim_ns,
                                self.setup_config["sim_layer"])]
        input_nodes = self.get_layer_nodes_info(layers)
        print(input_nodes.values()[0])
        return self.is_node_cache(input_nodes.values()[0])

    def is_node_cache(self, nodes):
        nodes_with_cache = []
        for node in nodes:
            for shape in cmds.listRelatives(node, shapes=True) or []:
                if cmds.listConnections(shape, type=["historySwitch",
                                                     "cacheFile"]):
                    nodes_with_cache.extend([node, shape])
        return nodes_with_cache

    def cache_sim_nodes(self, nodes, start_frame, end_frame):
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
        cache_cmd = 'doCreateNclothCache 5 {{ "0", "{start_frame}", "{end_frame}", "OneFile", "1", "{cache_dir}", "1", "", "0", "replace", "1", "1", "1","0","1","mcx" }};'

        cache_arg_info = {
            "start_frame": start_frame,
            "end_frame": end_frame,
            "cache_dir": self.setup_config["cache_dir"]
        }

        cache_cmd = cache_cmd.format(**cache_arg_info)
        cmds.select(nodes)
        mel.eval(cache_cmd)
