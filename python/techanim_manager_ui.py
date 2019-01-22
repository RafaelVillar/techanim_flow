# -*- coding: utf-8 -*-
# Standard
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import generators
from __future__ import division

import os
import sys
from functools import wraps

import maya.cmds as cmds

from PySide2 import QtWidgets, QtCore, QtGui

import ui_utils
import creator_utils
import techanim_manager_utils

reload(ui_utils)
reload(creator_utils)
reload(techanim_manager_utils)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
CONFIG = creator_utils.CONFIG

LONG_NAME_INT = 100
NODE_TYPE_INT = 200
DISPLAY_NODE_INT = 300

VIEW_LIST_ITEM_MSG = """
NodeType: {nodeType}
childTypes: {childTypes}
"""

DIR_PATH = os.path.dirname(__file__)
WINDOW_TITLE = "TechAnim Setup Manager"
HOWTO_FILEPATH_DICT = CONFIG.get("HOWTO_FILEPATH_DICT", {})
NULL_SETUP_SELCT_TEXT = "Select TechAnim Setup"

for _key, _path in HOWTO_FILEPATH_DICT.iteritems():
    HOWTO_FILEPATH_DICT[_key] = os.path.join(DIR_PATH, os.path.normpath(_path))


def show(hide_menu=False, *args):
    """To launch the ui and not get the same instance

    Returns:
        DistributeUI: instance

    Args:
        *args: Description
    """
    # global TECH_CREATOR_UI
    try:
        ui_utils.close_existing(class_name="TechAnimSetupManagerUI")
    except Exception:
        pass
    maya_window = ui_utils.mainWindow() or None
    TECH_UI = TechAnimSetupManagerUI(parent=maya_window, hide_menu=hide_menu)
    TECH_UI.show()
    TECH_UI.adjustSize()
    return TECH_UI


class TechAnimSetupManagerUI(QtWidgets.QDialog):

    green_color = QtGui.QColor(23, 158, 131)
    grey_color = QtGui.QColor(225, 225, 225)

    def __init__(self, parent=None, hide_menu=False):
        super(TechAnimSetupManagerUI, self).__init__(parent=parent)
        self.parent = parent
        self.setWindowTitle(WINDOW_TITLE)
        self.setObjectName(self.__class__.__name__)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowFlags(self.windowFlags())

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)

        self.mainLayout.addWidget(self.setup_selector_widget())
        self.mainLayout.addWidget(self.frame_range_widget())
        self.mainLayout.addLayout(self.input_layer_layout())
        self.mainLayout.addWidget(self.views_layout())
        self.mainLayout.addWidget(self.create_ncahe_widget())
        if hide_menu:
            self.mainLayout.setMenuBar(self.menu_bar_widget(hideable=hide_menu))

        self.techanim_setup_nodes = []
        self.techanim_view_widgets = []
        self.active_setup = None

        self.reconnect_signals()

    @property
    def total_start_frame(self):
        """Start from with the pre roll subtracted

        Returns:
            int: Start from with the pre roll subtracted
        """
        return self.start_frame_sb.value() - self.preroll_sb.value()

    @property
    def total_end_frame(self):
        """Total end fraame with post roll added

        Returns:
            TYPE: Total end fraame with post roll added
        """
        return self.end_frame_sb.value() + self.postroll_sb.value()

    @property
    def start_frame(self):
        """start frame based on scene range or as edited by the user

        Returns:
            TYPE: start frame based on scene range or as edited by the user
        """
        return self.start_frame_sb.value()

    @property
    def end_frame(self):
        """end frame based on scene range or as edited by the user

        Returns:
            TYPE: end frame based on scene range or as edited by the user
        """
        return self.end_frame_sb.value()

    def check_for_active(func):
        """Convenience function to test if there is an active TechAnim_setup
        node.

        Args:
            func (function): function getting wrapped

        Returns:
            func: same function passed in, provided there is an active seup
        """
        @wraps(func)
        def check_active(self, *args, **kwargs):
            if self.active_setup is None:
                msg = "No Techanim Setup selected in the UI."
                ui_utils.genericWarning(self, msg)
                return None
            else:
                return func(self, *args, **kwargs)
        return check_active

    def reconnect_signals(self):
        """Reconnect signals upon refresh
        """
        try:
            self.cache_input_layer_btn.clicked.disconnect()
        except RuntimeError:
            pass
        self.cache_input_layer_btn.clicked.connect(self._cache_input_layer)
        self.delete_input_layer_btn.clicked.connect(self._delete_cache_input_layer)
        self.setup_select_cb.currentIndexChanged.connect(self.setup_selection_changed)
        self.create_ncache_btn.clicked.connect(self.create_ncache)
        self.delete_ncache_btn.clicked.connect(self.delete_ncache)
        self.refresh_btn.clicked.connect(self.total_refresh)

    @check_for_active
    def _cache_input_layer(self):
        """Cache the input layer nodes. All of them.
        """
        self.active_setup.cache_input_layer(self.total_start_frame,
                                            self.total_end_frame)
        self.color_input_cache_button()

    @check_for_active
    def _delete_cache_input_layer(self):
        """Cache the input layer nodes. All of them.
        """
        self.active_setup.delete_input_layer_cache()
        self.color_input_cache_button()

    def delete_layers_widgets(self):
        """Upon refresh, delete the listview displaying their contents
        """
        layer_widgets = self.views_widget.layout().children()
        layer_widgets.extend(self.views_widget.children()[1:])
        for wdgt in layer_widgets:
            wdgt.deleteLater()
        self.techanim_view_widgets = []
        self.sim_view_widget = None

    def total_refresh(self):
        """Convenience function to avoid partials
        """
        self.refresh(collected_setups=True)

    def refresh(self, collected_setups=False):
        """Refresh the UI and research for techanim setup nodes

        Args:
            collected_setups (bool, optional): Refresh without recollecting

        Returns:
            None: If there are no active setups chosen, skip the rest
        """
        if collected_setups:
            print("Re-Collecting techanim_setups...")
            self.get_techanim_setups()
            self.populate_setup_list()
        self.setup_selection_changed()
        if not self.active_setup:
            return
        self.set_sim_view_info()
        self.color_sim_view()
        self.color_input_cache_button()

    def color_sim_view(self):
        """Color qlistwidgentitems depending on the sim node they represent
        """
        blank = QtGui.QBrush()
        blank.setColor(self.grey_color)
        green_brush = QtGui.QBrush()
        green_brush.setColor(self.green_color)
        cached_nodes = self.active_setup.is_sim_layer_cached()
        for index in range(self.sim_view_widget.count()):
            item = self.sim_view_widget.item(index)
            short_name = creator_utils.removeNS(item.data(LONG_NAME_INT))
            if item.data(LONG_NAME_INT) in cached_nodes:
                italic = True
                text = "{} (Cached)".format(short_name)
            else:
                italic = False
                text = short_name

            font = item.font()
            font.setItalic(italic)
            item.setFont(font)
            item.setText(text)

    def color_input_cache_button(self):
        """If the input layer is cached, color it green, grey if not.
        """
        text = "Input Layer is NOT Cached"
        color = self.grey_color.darker(250)

        if self.active_setup.is_input_layer_cached():
            text = "Input Layer is Cached"
            color = self.green_color

        self.cache_input_layer_btn.setText(text)
        button_palette = self.cache_input_layer_btn.palette()
        button_palette.setColor(QtGui.QPalette.Button, color)
        self.cache_input_layer_btn.setPalette(button_palette)
        self.cache_input_layer_btn.update()

    def populate_setup_list(self):
        """Populate the combobox of techanim setups
        """
        self.setup_select_cb.blockSignals(True)
        self.setup_select_cb.clear()
        self.setup_select_cb.insertItem(0, NULL_SETUP_SELCT_TEXT)
        [self.setup_select_cb.addItem(str(x))
            for x in self.techanim_setup_nodes]
        self.setup_select_cb.blockSignals(False)

    def setup_selection_changed(self, *args):
        """If the user makes a change on the current selection, refresh
        as needed

        Args:
            *args: throwaway from signal

        Returns:
            None: If a setup not chosen, returns before we refresh things
            that require a setup
        """
        setup_name = self.setup_select_cb.currentText()
        if setup_name == NULL_SETUP_SELCT_TEXT:
            self.active_setup = None
            self.delete_layers_widgets()
            return
        for setup_node in self.techanim_setup_nodes:
            if setup_node.root_node == setup_name:
                self.active_setup = setup_node
                self.activate_setup(setup_node)
        self.color_input_cache_button()
        self.set_sim_view_info()
        self.color_sim_view()

    def views_layout(self):
        """create the views layout

        Returns:
            QGroupbox: So it can be parented where needed
        """
        self.views_widget = QtWidgets.QGroupBox("Layer Nodes")
        self.views_widget.setLayout(QtWidgets.QHBoxLayout())
        return self.views_widget

    def order_sim_view(self):
        """Order the contents of the simview as desired. Nucleus first
        everything alphabetical after that
        """
        nuc_list = []
        # This makes all nuclei nodes the first in the list
        for index in range(self.sim_view_widget.count()):
            item = self.sim_view_widget.item(index)
            if item.data(NODE_TYPE_INT) == "nucleus":
                nuc_list.append(item)

        for x in nuc_list:
            index = self.sim_view_widget.row(x)
            self.sim_view_widget.takeItem(index)
            self.sim_view_widget.insertItem(0, x)

    def set_sim_view_info(self):
        """Add information to each Qlistwidgetitem based on the node it
        represents
        """
        display_suffix = self.active_setup.setup_config["nCloth_output_suffix"]
        auto_select_display = False
        if display_suffix in self.active_setup.suffixes_to_hide:
            auto_select_display = True

        for layer_layout, layer_view in self.techanim_view_widgets:
            for index in range(layer_view.count()):
                item = layer_view.item(index)
                node_name = item.data(LONG_NAME_INT)
                node_type = item.data(NODE_TYPE_INT)
                if auto_select_display and not node_name.endswith(display_suffix):
                    display_node = "{}{}".format(node_name, display_suffix)
                    if cmds.objExists(display_node):
                        item.setData(DISPLAY_NODE_INT, display_node)
                children = cmds.listRelatives(node_name, shapes=True) or []
                child_types = [str(cmds.nodeType(x)) for x in children]
                msg = VIEW_LIST_ITEM_MSG.format(nodeType=node_type,
                                                childTypes=child_types)
                item.setToolTip(msg)
        self.order_sim_view()

    def activate_setup(self, setup_node):
        """Populate the layer views with child nodes

        Args:
            setup_node (TechAnim_setup): Which setup to pull information from
        """
        self.delete_layers_widgets()
        if not setup_node.is_setup_connected():
            namespaces = techanim_manager_utils.get_all_target_namespaces()
            ns_prompt = ui_utils.GenericSelectionUI("Choose target namespace",
                                                    namespaces,
                                                    parent=self)
            results = ns_prompt.exec_()
            setup_node.set_target_namespace(results[0])
        setup_node.refresh_info()
        layers_info = setup_node.get_layer_nodes_info(setup_node.sim_layers)
        for layer_name in setup_node.sim_layers:
            nodes = layers_info[layer_name]
            layer_layout, layer_view = self.layer_view_widget(layer_name,
                                                              nodes)
            if creator_utils.removeNS(layer_name) == setup_node.setup_config["sim_layer"]:
                self.sim_view_widget = layer_view
                msg = "{} is your nCloth layer. Other layers are for clean-up."
                msg = msg.format(layer_name)
                self.sim_view_widget.setToolTip(msg)

            # color views
            bg_color = self.views_widget.palette().color(self.views_widget.backgroundRole())
            sBox_palette = layer_view.palette()
            sBox_palette.setColor(QtGui.QPalette.Base, bg_color.darker(110))
            layer_view.setPalette(sBox_palette)

            self.views_widget.layout().addLayout(layer_layout)
            self.techanim_view_widgets.append([layer_layout, layer_view])

    def get_techanim_setups(self):
        """Get all techanim setups in the scene, no duplicates

        Returns:
            list: of found TechAnim_Setup nodes
        """
        tmp = techanim_manager_utils.get_all_setups_nodes()
        self.techanim_setup_nodes = list(set(tmp))
        return self.techanim_setup_nodes

    def hide_menubar(self, x, y):
        """rules to hide/show the menubar when hide is enabled

        Args:
            x (int): coord X of the mouse
            y (int): coord Y of the mouse
        """
        if x < 100 and y < 50:
            self.main_menubar.show()
        else:
            self.main_menubar.hide()

    def menu_bar_widget(self, hideable=False):
        """Creates a menubar for options to added to. Currently not enough
        options for it to be needed, default off.

        Args:
            hideable (bool, optional): Have the menubar be hideable

        Returns:
            QMenubar: teh menu
        """
        self.main_menubar = QtWidgets.QMenuBar(self)
        file_menu = self.main_menubar.addMenu("File")
        file_menu.addAction("Refresh", self.total_refresh)

        if hideable:
            self.main_menubar.hide()
            self.hideable_mouse = hideable
            self.setMouseTracking(hideable)
        return self.main_menubar

    def setup_selector_widget(self):
        """Top portion of the widget where the use selects the active setup

        Returns:
            QGroupBox: To be parented where needed
        """
        group_widget = QtWidgets.QGroupBox("Select TechAnim Setup")
        layout = QtWidgets.QHBoxLayout()
        self.setup_select_cb = QtWidgets.QComboBox()
        self.setup_select_cb.setMaximumHeight(30)
        select_label = QtWidgets.QLabel("Active Setup:")
        self.refresh_btn = QtWidgets.QPushButton()
        self.refresh_btn.setMaximumWidth(30)
        self.refresh_btn.setMaximumHeight(26)
        style = QtWidgets.QStyle
        self.refresh_btn.setIcon(self.style().standardIcon(getattr(style, "SP_BrowserReload")))
        layout.addWidget(select_label)
        layout.addWidget(self.setup_select_cb)
        layout.addWidget(self.refresh_btn)
        group_widget.setLayout(layout)
        group_widget.setMaximumHeight(60)
        return group_widget

    def frame_range_widget(self):
        """Frame selection widget for user input

        Returns:
            QGroupBox: to be parented where needed
        """
        group_widget = QtWidgets.QGroupBox("Frame Range Settings")
        no_buttons = QtWidgets.QAbstractSpinBox.NoButtons

        layout = QtWidgets.QHBoxLayout()
        group_widget.setLayout(layout)
        self.preroll_sb = QtWidgets.QSpinBox()
        self.preroll_sb.setPrefix("Pre Roll: ")
        self.preroll_sb.setMaximum(100000)
        self.preroll_sb.setMinimum(0)
        self.preroll_sb.setValue(CONFIG["preroll"])
        self.preroll_sb.setButtonSymbols(no_buttons)
        self.preroll_sb.setToolTip("How many preroll frames before action.")

        self.start_frame_sb = QtWidgets.QSpinBox()
        self.start_frame_sb.setPrefix("Start Frame: ")
        self.start_frame_sb.setMaximum(100000)
        self.start_frame_sb.setMinimum(-100000)
        self.start_frame_sb.setValue(cmds.playbackOptions(min=True, q=True))
        self.start_frame_sb.setButtonSymbols(no_buttons)
        self.start_frame_sb.setToolTip("When the action or shot starts.")

        self.end_frame_sb = QtWidgets.QSpinBox()
        self.end_frame_sb.setPrefix("End Frame: ")
        self.end_frame_sb.setMaximum(100000)
        self.end_frame_sb.setMinimum(-100000)
        self.end_frame_sb.setValue(cmds.playbackOptions(max=True, q=True))
        self.end_frame_sb.setButtonSymbols(no_buttons)
        self.end_frame_sb.setToolTip("When the action or shot ends.")

        bg_color = group_widget.palette().color(group_widget.backgroundRole())
        sBox_palette = self.start_frame_sb.palette()
        sBox_palette.setColor(QtGui.QPalette.Base, bg_color)
        self.start_frame_sb.setPalette(sBox_palette)
        self.end_frame_sb.setPalette(sBox_palette)

        self.postroll_sb = QtWidgets.QSpinBox()
        self.postroll_sb.setPrefix("Post Roll: ")
        self.postroll_sb.setMaximum(100000)
        self.postroll_sb.setMinimum(0)
        self.postroll_sb.setValue(CONFIG["postroll"])
        self.postroll_sb.setButtonSymbols(no_buttons)
        self.postroll_sb.setToolTip("How many postroll frames after action.")

        layout.addWidget(self.preroll_sb)
        layout.addWidget(self.start_frame_sb)
        layout.addWidget(self.end_frame_sb)
        layout.addWidget(self.postroll_sb)

        return group_widget

    def input_layer_layout(self):
        """Options for the input layer, create or delete cached

        Returns:
            QVBoxLayout: For parenting where needed
        """
        layout = QtWidgets.QVBoxLayout()
        msg = "Cache Input Layer"
        self.cache_input_layer_btn = QtWidgets.QPushButton(msg)
        self.cache_input_layer_btn.setAutoFillBackground(True)
        msg = "Caches source geometry, will ignore rig/alembic afterwards."
        self.cache_input_layer_btn.setToolTip(msg)

        msg = "Delete input layer cache"
        self.delete_input_layer_btn = QtWidgets.QPushButton(msg)
        msg = "Delete if you want to update source animation."
        self.delete_input_layer_btn.setToolTip(msg)
        layout.addWidget(self.cache_input_layer_btn)
        layout.addWidget(self.delete_input_layer_btn)

        return layout

    def layer_view_widget(self, layer_name, nodes):
        """Create the view layer widget representing the layers in the setup.
        Populated with the children nodes

        Args:
            layer_name (str): name of desired layer
            nodes (list): of nodes to add to view

        Returns:
            list: [Qlayout, QListWidget]
        """
        layer_layout = QtWidgets.QVBoxLayout()
        layer_label = QtWidgets.QLabel(creator_utils.removeNS(layer_name).capitalize())
        layer_view = QtWidgets.QListWidget()
        layer_view.setObjectName(layer_name)
        layer_view.currentItemChanged.connect(self.select_node)
        layer_view.itemClicked.connect(self.select_node)
        nodes.sort()

        for node in nodes:
            if node in self.active_setup.nodes_to_hide:
                continue
            elif [x for x in self.active_setup.suffixes_to_hide if node.endswith(x)]:
                continue
            node_item = QtWidgets.QListWidgetItem(creator_utils.removeNS(node))
            node_type = cmds.nodeType(node)
            node_item.setData(LONG_NAME_INT, node)
            node_item.setData(NODE_TYPE_INT, node_type)
            node_item.setData(DISPLAY_NODE_INT, None)
            layer_view.addItem(node_item)
        selType = QtWidgets.QAbstractItemView.ExtendedSelection
        layer_view.setSelectionMode(selType)
        layer_layout.addWidget(layer_label)
        layer_layout.addWidget(layer_view)

        return layer_layout, layer_view

    @check_for_active
    def delete_ncache(self):
        """Delete ncache on the selected ncloth nodes
        """
        suffix = self.active_setup.setup_config["nCloth_suffix"]
        to_cache = []
        for item in self.sim_view_widget.selectedItems():
            node_name = item.data(LONG_NAME_INT)
            if not node_name.endswith(suffix):
                continue
            to_cache.append(item.data(LONG_NAME_INT))
        self.active_setup.delete_sim_cache(to_cache)
        self.color_sim_view()

    @check_for_active
    def create_ncache(self):
        """cache selected ncloth nodes from the setup

        Returns:
            None: if not a setup ncloth node skip
        """
        suffix = self.active_setup.setup_config["nCloth_suffix"]
        to_cache = []
        for item in self.sim_view_widget.selectedItems():
            node_name = item.data(LONG_NAME_INT)
            if not node_name.endswith(suffix):
                continue
            to_cache.append(item.data(LONG_NAME_INT))
        if not to_cache:
            msg = "No nCloth <node>{} nodes selected!".format(suffix)
            ui_utils.genericWarning(self, msg)
            return
        self.active_setup.set_start_nuclei_frame(self.total_start_frame)
        self.active_setup.cache_sim_nodes(to_cache,
                                          self.total_start_frame,
                                          self.total_end_frame)
        self.active_setup.set_start_nuclei_frame(self.start_frame)
        self.color_sim_view()

    def create_ncahe_widget(self):
        """nCache settings widget

        Returns:
            QGroupWidget: settings widget
        """
        group_widget = QtWidgets.QGroupBox("nCache settings")
        layout = QtWidgets.QVBoxLayout()
        group_widget.setLayout(layout)
        self.create_ncache_btn = QtWidgets.QPushButton("Create nCache")
        self.delete_ncache_btn = QtWidgets.QPushButton("Delete nCache")
        layout.addWidget(self.create_ncache_btn)
        layout.addWidget(self.delete_ncache_btn)
        self.create_ncache_btn.setMinimumWidth(150)
        self.create_ncache_btn.setMaximumWidth(250)
        self.delete_ncache_btn.setMinimumWidth(150)
        self.delete_ncache_btn.setMaximumWidth(250)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        return group_widget

    def select_node(self, selection_item):
        """Select the node listed on the listwidget

        Args:
            selection_item (QListwidgetItem): selected
        """
        current_view = selection_item.listWidget()
        to_sel = []
        for item in current_view.selectedItems():
            to_sel.append(item.data(LONG_NAME_INT))
            display_node = item.data(DISPLAY_NODE_INT)
            if display_node:
                to_sel.append(display_node)

        self.active_setup.show_nodes(to_sel, select=True)
        for layer_layout, layer_view in self.techanim_view_widgets:
            if current_view == layer_view:
                continue
            layer_view.clearSelection()

    # =========================================================================
    # overrides
    # =========================================================================

    def mouseMoveEvent(self, event):
        """used for tracking the mouse position over the UI, in this case for
        menu hiding/show

        Args:
            event (Qt.QEvent): events to filter
        """
        if event.type() == QtCore.QEvent.MouseMove:
            if event.buttons() == QtCore.Qt.NoButton:
                pos = event.pos()
                self.hide_menubar(pos.x(), pos.y())

    def show(self):
        """Refresh the ui after it has been displayed
        """
        super(TechAnimSetupManagerUI, self).show()
        self.refresh(collected_setups=True)


if __name__ == '__main__':
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    qapp = QtWidgets.QApplication(sys.argv)
    import maya.standalone
    maya.standalone.initialize("Python")
    cmds.loadPlugin("mtoa", qt=True)
    qapp.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    qapp.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    tac_UI = show()
    sys.exit(qapp.exec_())
