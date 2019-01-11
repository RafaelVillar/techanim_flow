# -*- coding: utf-8 -*-
# Standard
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import generators
from __future__ import division

import os

import maya.cmds as cmds

try:
    from Qt import QtWidgets, QtCore
except Exception:
    from PySide2 import QtWidgets, QtCore

import ui_utils
import creator_utils
import techanim_manager_utils

reload(creator_utils)
reload(techanim_manager_utils)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
CONFIG = creator_utils.CONFIG

DIR_PATH = os.path.dirname(__file__)
WINDOW_TITLE = "TechAnim Setup Manager"
HOWTO_FILEPATH_DICT = CONFIG.get("HOWTO_FILEPATH_DICT", {})

for _key, _path in HOWTO_FILEPATH_DICT.iteritems():
    HOWTO_FILEPATH_DICT[_key] = os.path.join(DIR_PATH, os.path.normpath(_path))


def show(*args):
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
    TECH_UI = TechAnimSetupManagerUI(parent=maya_window)
    TECH_UI.show()
    TECH_UI.adjustSize()
    return TECH_UI


class GenericSelectionUI(QtWidgets.QDialog):

    """Allow the user to select which attrs will drive the rbf nodes in a setup

    Attributes:
        drivenListWidget (QListWidget): widget to display attrs to drive setup
        okButton (QPushButton): BUTTON
        result (list): of selected attrs from listWidget
        setupField (bool)): Should the setup lineEdit widget be displayed
        setupLineEdit (QLineEdit): name selected by user
    """

    def __init__(self, namespaces, parent=None):
        """setup the UI widgets

        Args:
            namespaces (list): attrs to be displayed on the list
            parent (QWidget, optional): widget to parent this to
        """
        super(GenericSelectionUI, self).__init__(parent=parent)
        self.setWindowTitle(TOOL_TITLE)
        mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(mainLayout)
        self.result = []
        #  --------------------------------------------------------------------
        setupLayout = QtWidgets.QHBoxLayout()
        setupLabel = QtWidgets.QLabel("Specify Target Namespace")
        #  --------------------------------------------------------------------
        drivenLayout = QtWidgets.QVBoxLayout()
        drivenLabel = QtWidgets.QLabel("Select Driven Attributes")
        self.drivenListWidget = QtWidgets.QListWidget()
        self.drivenListWidget.addItems(namespaces)
        drivenLayout.addWidget(drivenLabel)
        drivenLayout.addWidget(self.drivenListWidget)
        mainLayout.addLayout(drivenLayout)
        #  --------------------------------------------------------------------
        # buttonLayout = QtWidgets.QHBoxLayout()
        self.okButton = QtWidgets.QPushButton("Ok")
        self.okButton.clicked.connect(self.onOK)
        mainLayout.addWidget(self.okButton)

    def onOK(self):
        """collect information from the displayed widgets, userinput, return

        Returns:
            list: of user input provided from user
        """
        selected_namespace = self.drivenListWidget.selectedItems()
        if not selected_namespace:
            genericWarning(self, "Select a namespaces!")
            return
        self.result.append(selected_namespace[0])
        self.accept()
        return self.result

    def getValue(self):
        """convenience to get result

        Returns:
            TYPE: Description
        """
        return self.result

    def exec_(self):
        """Convenience

        Returns:
            list: [str, [of selected attrs]]
        """
        super(GenericSelectionUI, self).exec_()
        return self.result


class TechAnimSetupManagerUI(QtWidgets.QDialog):
    """docstring for TechAnimSetupManagerUI"""
    def __init__(self, parent=None):
        super(TechAnimSetupManagerUI, self).__init__(parent=parent)
        self.parent = parent
        self.setWindowTitle(WINDOW_TITLE)
        self.setObjectName(self.__class__.__name__)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowFlags(self.windowFlags())

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.setup_selector_widget())
        self.views_widget = self.views_layout()
        self.mainLayout.addWidget(self.views_widget)

        self.techanim_setup_nodes = []
        self.techanim_view_widgets = []
        self.active_setup = None

        self.refresh(collected_setups=True)

    def delete_layers_widgets(self):
        for widget in self.techanim_view_widgets:
            widget.deleteLater()
        self.techanim_view_widgets = []

    def refresh(self, collected_setups=False):
        if collected_setups:
            self.get_techanim_setups()
            self.populate_setup_list()
        self.setup_selection_changed()

    def populate_setup_list(self):
        self.setup_select_cb.clear()
        print(self.techanim_setup_nodes)
        [self.setup_select_cb.addItem(str(x))
            for x in self.techanim_setup_nodes]

    def setup_selection_changed(self, *args):
        setup_name = self.setup_select_cb.currentText()
        for setup_node in self.techanim_setup_nodes:
            if setup_node.root_node == setup_name:
                self.active_setup = setup_node
                self.populate_layers_widgets(setup_node)

    def views_layout(self):
        group_widget = QtWidgets.QGroupBox("Layer Nodes")
        group_widget.setLayout(QtWidgets.QHBoxLayout())
        return group_widget

    def populate_layers_widgets(self, setup_node):
        self.delete_layers_widgets()
        if not setup_node.is_setup_connected():
            namespaces = techanim_manager_utils.get_all_namespaces()
            results = GenericSelectionUI(namespaces, parent=self)
            setup_node.set_target_namespace(results[0])
        setup_node.refresh_info()
        layers_info = setup_node.get_layer_nodes_info(setup_node.sim_layers)
        for layer_name in setup_node.sim_layers:
            nodes = layers_info[layer_name]
            layer_layout, layer_view = self.layer_view_widget(layer_name,
                                                              nodes)
            self.views_widget.layout().addLayout(layer_layout)
            self.techanim_view_widgets.append([layer_layout, layer_view])

    def get_techanim_setups(self):
        tmp = techanim_manager_utils.get_all_setups_nodes()
        self.techanim_setup_nodes = list(set(tmp))
        return self.techanim_setup_nodes

    def setup_selector_widget(self):
        group_widget = QtWidgets.QGroupBox("Select TechAnim Setup")
        layout = QtWidgets.QHBoxLayout()
        self.setup_select_cb = QtWidgets.QComboBox()
        select_label = QtWidgets.QLabel("Active Setup:")
        layout.addWidget(select_label)
        layout.addWidget(self.setup_select_cb)
        group_widget.setLayout(layout)
        group_widget.setMaximumHeight(60)
        return group_widget

    def layer_view_widget(self, layer_name, nodes):
        layer_layout = QtWidgets.QVBoxLayout()
        layer_label = QtWidgets.QLabel(layer_name)
        layer_view = QtWidgets.QListWidget()
        layer_view.currentItemChanged.connect(self.select_node)
        for node in nodes:
            node_item = QtWidgets.QListWidgetItem(creator_utils.removeNS(node))
            node_item.setData(100, node)
            print(node_item.data(100))
            layer_view.addItem(node_item)
        layer_layout.addWidget(layer_label)
        layer_layout.addWidget(layer_view)

        return layer_layout, layer_view

    def select_node(self, selection_item):
        self.active_setup.show_nodes(selection_item.data(100), select=True)
        # cmds.select()