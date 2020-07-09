# -*- coding: utf-8 -*-
"""UI for creating a Techanim setup. This the flexibility in these tools comes
from the config. The "setup" is very specific, but the naming of things is not.

Attributes:
    CONFIG (dict): either default or from env variable
    DIR_PATH (str): parent path
    HOWTO_FILEPATH_DICT (dict): filename: filepath of images to display in
        the ui
    WINDOW_TITLE (str): Name of the UI
"""
# Standard
from __future__ import division
from __future__ import generators
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import ast
import copy

from functools import partial

import maya.cmds as cmds

try:
    from Qt import QtWidgets, QtGui, QtCore
except Exception:
    from PySide2 import QtWidgets, QtGui, QtCore

from techanim_flow import ui_utils
from techanim_flow import config_io
from techanim_flow import techanim_creator_utils
reload(config_io)
reload(ui_utils)
reload(techanim_creator_utils)


# =============================================================================
# Constants
# =============================================================================
CONFIG = config_io.CONFIG

WINDOW_TITLE = "TechAnim Creator"
DIR_PATH = os.path.dirname(__file__)
TECH_PYTHON_PATH = os.path.abspath(os.path.join(DIR_PATH, os.pardir))
ROOT_MODULE_PATH = os.path.abspath(os.path.join(TECH_PYTHON_PATH, os.pardir))
HOWTO_FILEPATH_DICT = CONFIG.get("HOWTO_FILEPATH_DICT", {})

WRAP_FALLOW_SETTINGS_DICT = {
    "surface": 0,
    "volume": 1
}


for _key, _path in HOWTO_FILEPATH_DICT.iteritems():
    HOWTO_FILEPATH_DICT[_key] = os.path.join(ROOT_MODULE_PATH,
                                             os.path.normpath(_path))




def show(*args):
    """To launch the ui and not get the same instance

    Returns:
        DistributeUI: instance

    Args:
        *args: Description
    """
    # global TECH_CREATOR_UI
    try:
        ui_utils.close_existing(class_name="TechAnimCreatorUI")
    except Exception:
        pass
    maya_window = ui_utils.mainWindow() or None
    TECH_UI = TechAnimCreatorUI(parent=maya_window)
    TECH_UI.show()
    TECH_UI.adjustSize()
    return TECH_UI


class DisplayImage(QtWidgets.QWidget):
    """Displays gif from provided path"""
    def __init__(self, parent=None):
        super(DisplayImage, self).__init__(parent=parent)
        self.parent = parent
        # IF parent was provided, install an event filter to keep sizing
        if self.parent:
            self.parent.installEventFilter(self)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 150);")
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        self.easter_get_path = None

        self.movie = None

        self.movie_screen = QtWidgets.QLabel()
        # Make label fit the gif
        self.movie_screen.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                        QtWidgets.QSizePolicy.Expanding)
        self.movie_screen.setAlignment(QtCore.Qt.AlignCenter)

        # Create the layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.movie_screen)

        self.setLayout(main_layout)

    def set_easter_get_path(self, filepath):
        """Lets have some fun, otherwise what the fuck are we doing.

        Args:
            filepath (str): path to image to dispaly
        """
        self.easter_get_path = filepath

    def show_easter_egg(self):
        """display the easter egg if path exists
        """
        if self.easter_get_path and os.path.exists(self.easter_get_path):
            self.display_gif(self.easter_get_path)

    def display_gif(self, filepath):
        """delete existing movie and replace with the provided path

        Args:
            filepath (str): of the path
        """
        # Load the file into a QMovie
        if self.movie:
            self.movie.deleteLater()
        self.movie = QtGui.QMovie(filepath, QtCore.QByteArray(), self)
        self.movie.setCacheMode(QtGui.QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.movie_screen.setMovie(self.movie)
        self.movie.start()
        self.show()

    def mousePressEvent(self, event):
        """click makes the layer with image disappear

        Args:
            event (QtCore.QEvent): standard event that gets passed
        """
        modifiers = event.modifiers()
        if event.buttons() == QtCore.Qt.LeftButton and modifiers == QtCore.Qt.ShiftModifier:
            self.show_easter_egg()
        elif event.buttons() == QtCore.Qt.LeftButton:
            self.hide()

    def eventFilter(self, QObject, QEvent):
        """Catch the WhatsThis even on any widget and display its howto layer

        Args:
            QObject (QtCore.QObject): standard qobject
            QEvent (QtCore.QEvent): standard event that gets added

        Returns:
            Bool: original super call
        """
        if QEvent.type() == QtCore.QEvent.Type.Resize:
            size = QObject.size()
            self.resize(size)

        return False


class AssociateSelectionControl(QtCore.QObject):
    """docstring for TechAnimCreatorModel """
    paired_created = QtCore.Signal()
    all_pairs_made = QtCore.Signal(bool)

    def __init__(self, viewA, viewB):
        super(AssociateSelectionControl, self).__init__()

        self.viewA = viewA
        self.modelA = QtGui.QStandardItemModel()
        self.viewA.setModel(self.modelA)

        self.modelB = QtGui.QStandardItemModel()
        self.viewB = viewB
        self.viewB.setModel(self.modelB)

        self.association_dict = {}

        self.all_recorded = False
        self.viewA.selectionModel().selectionChanged.connect(self.highlight_associated)
        self.viewB.clicked.connect(self.check_create_entry)

    def filter_dupicates(self, items):
        """ensure there are no duplicate pieces of geometry in the UI

        Args:
            items (list): of str names to check

        Returns:
            list: of names not already recorded in the models
        """
        safe_to_add = []
        already_added = []
        for item in items:
            if self.modelA.findItems(item) or self.modelB.findItems(item):
                already_added.append(item)
            else:
                safe_to_add.append(item)
        return list(set(safe_to_add)), list(set(already_added))

    def add_items(self, model, items):
        """Add provided items to the provided model, provided they are not
        already recorded

        Args:
            model (QtGui.QStandardItemModel): where to add items to
            items (list): of items to add
        """
        safe_to_add, already_added = self.filter_dupicates(items)
        for item in safe_to_add:
            model.appendRow(QtGui.QStandardItem(item))
        if already_added:
            msg = "Skipping duplicates! {}".format(already_added)
            print(self.tr(msg))

    def remove_associated_items(self, items):
        """remove any items from the controllers association_dict

        Args:
            items (list): of items to remove
        """
        to_remove = []
        for key, value in self.association_dict.iteritems():
            for item in items:
                if item in [key, value]:
                    to_remove.append(key)
        [self.association_dict.pop(x) for x in to_remove]

    def remove_selected(self, view):
        """Remove the currently selected item in the view

        Args:
            view (QtGui.qListview): to query
        """
        modelIndex = view.selectedIndexes()
        model = view.model()
        if modelIndex:
            row = modelIndex[0].row()
            item_text = modelIndex[0].data()
            self.remove_associated_items([item_text])
            model.takeRow(row)
        self.viewA.selectionModel().clear()
        self.viewB.selectionModel().clear()
        self.slant_entries()

    def remove_items(self, model, items):
        """Remove a list of items from the provided model and provided list

        Args:
            model (QtGUi.QStandardItemModel): model to remove from
            items (list): of names to remove
        """
        for item in items:
            desired_item = model.findItems(item)
            if desired_item:
                model.takeRow(desired_item.row())
        self.remove_associated_items(items)
        self.viewA.selectionModel().clear()
        self.viewB.selectionModel().clear()

    def highlight_associated(self, itemSelectionA, itemSelectionB):
        """select the item associated to the selection in the
        render_geo qlistview within the sim qlistview

        Args:
            itemSelectionA (QtGui.QStandardItem): automatically passsed from
            signal, not used here
            itemSelectionB (QtGui.QStandardItem): automatically passsed from
            signal, not used here

        Returns:
            n/a: n/a
        """
        modelIndex = self.viewA.selectedIndexes()
        if modelIndex:
            modelIndex = modelIndex[0]
        else:
            return
        model = modelIndex.model()
        self.viewB.selectionModel().clear()
        item_name = model.itemData(modelIndex)[0]
        if item_name in self.association_dict:
            associated_item = self.association_dict[item_name]
            desired_item = self.modelB.findItems(associated_item)[0]
            modelIndexB = self.modelB.indexFromItem(desired_item)
            sel_type = QtCore.QItemSelectionModel.Select
            self.viewB.selectionModel().select(modelIndexB, sel_type)

    def make_italic(self, model, compare_list):
        """Go through the childen of the provided model, and if they are in
        the compare list make them italic

        Args:
            model (QtGui.QStandardItemModel): model to quary data
            compare_list (list): list to compare against
        """
        for index in xrange(model.rowCount()):
            item = model.item(index)
            if item.data(0) in compare_list:
                ital = True
            else:
                ital = False
            font = item.font()
            font.setItalic(ital)
            item.setFont(font)

    def slant_entries(self, *args):
        """Convenience function to check both models against dict

        Args:
            *args: ignoring signal args
        """
        self.make_italic(self.modelA,
                         self.association_dict.keys())
        self.make_italic(self.modelB,
                         self.association_dict.values())

    def is_list_complete(self):
        """Have all the associations been made
        """
        if self.check_all_recorded():
            self.all_recorded = False
        else:
            self.all_recorded = True
        self.all_pairs_made.emit(self.all_recorded)

    def check_all_recorded(self):
        """Check all the associations for any missing pairs

        Returns:
            list: of non associated list items
        """
        missing = []
        for index in xrange(self.modelA.rowCount()):
            modelIndex = self.modelA.index(index, 0)
            index_text = modelIndex.data(0)
            if index_text not in self.association_dict:
                missing.append(index_text)
        return missing

    def check_create_entry(self, modelIndex):
        """check the association dict for any existing mention of either new
        pair, remove and make the new one

        Args:
            modelIndex (QtGui.modelIndex): connected to a signal

        Returns:
            n/a: nada
        """
        modelIndexA = self.viewA.selectedIndexes()
        if modelIndexA:
            modelIndexA = modelIndexA[0]
        else:
            return
        modelA = modelIndexA.model()
        modelB = modelIndex.model()
        render_geo = modelA.itemData(modelIndexA)[0]
        sim_geo = modelB.itemData(modelIndex)[0]

        # removing all occurrances of other mentions of selected
        to_remove = []
        for key, value in self.association_dict.iteritems():
            if value == sim_geo:
                to_remove.append(key)
        [self.association_dict.pop(x) for x in to_remove]
        self.association_dict[render_geo] = sim_geo
        self.is_list_complete()
        self.paired_created.emit()

    def testP(self, *args):
        print("test")
        print(args)


class TechAnimCreatorUI(QtWidgets.QDialog):
    """docstring for TechAnimCreatorUI"""
    def __init__(self, parent=None):
        super(TechAnimCreatorUI, self).__init__(parent=parent)
        self.parent = parent
        self.setWindowTitle(WINDOW_TITLE)
        self.setObjectName(self.__class__.__name__)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)

        self.mainLayout.addWidget(self.load_techanim_info_layout())
        self.mainLayout.addLayout(self.geo_selection_layout())
        self.mainLayout.addWidget(self.nCloth_settings_widget())
        self.mainLayout.addWidget(self.wrap_settings_layout())

        self.mainLayout.addWidget(self.create_setup_options_widget())
        self.mainLayout.addWidget(self.utils_layout())
        self.associate_control = AssociateSelectionControl(self.render_geo_view,
                                                           self.sim_geo_view)
        # setup options -------------------------------------------------------
        self.setup_options = {
            "falloffMode": self.wrap_falloff_cb,
            "exclusiveBind": self.wrap_exclusive_cb,
            "postScriptPath": self.post_script_edit,
            "nClothMapsPaths": self.ncloth_maps_edit
        }


        # attach signals and filters ------------------------------------------
        self.create_signal_connections()
        self.render_geo_view.installEventFilter(self)
        self.sim_geo_view.installEventFilter(self)
        self.add_driven_nodes_btn.installEventFilter(self)

        # howto layer ---------------------------------------------------------
        self.movie_screen = DisplayImage(parent=self)
        ee_path = HOWTO_FILEPATH_DICT.get("easter_egg")
        self.movie_screen.set_easter_get_path(ee_path)
        self.movie_screen.hide()

    def create_signal_connections(self):
        """Create signals connections for the UI
        """
        as_co = self.associate_control
        # connections ---------------------------------------------------------
        self.user_techanim_info_button.clicked.connect(self.load_user_techanim_info)
        as_co.viewA.clicked.connect(self.select_from_list)
        as_co.viewB.clicked.connect(self.select_from_list)

        as_co.modelA.rowsInserted.connect(self.update_render_label)
        as_co.modelA.rowsRemoved.connect(self.update_render_label)
        as_co.modelA.rowsInserted.connect(as_co.slant_entries)
        as_co.modelA.rowsRemoved.connect(as_co.slant_entries)

        as_co.modelB.rowsInserted.connect(self.update_geo_label)
        as_co.modelB.rowsRemoved.connect(self.update_geo_label)
        as_co.modelB.rowsInserted.connect(as_co.slant_entries)
        as_co.modelB.rowsRemoved.connect(as_co.slant_entries)

        as_co.paired_created.connect(as_co.slant_entries)

        render_model = self.render_geo_view.model()
        sim_model = self.sim_geo_view.model()
        self.render_geo_add_btn.clicked.connect(partial(self.add_selection,
                                                        as_co,
                                                        render_model))

        remove_sel = as_co.remove_selected
        self.render_geo_remove_btn.clicked.connect(partial(remove_sel,
                                                           self.render_geo_view))

        self.sim_geo_add_btn.clicked.connect(partial(self.add_selection,
                                                     as_co,
                                                     sim_model))

        self.sim_geo_remove_btn.clicked.connect(partial(remove_sel,
                                                        self.sim_geo_view))

        self.add_passive_btn.clicked.connect(self.add_passive_geo)

        as_co.all_pairs_made.connect(self.create_btn.setEnabled)
        self.ncloth_maps_button.clicked.connect(self.load_files_dialog)
        self.post_script_button.clicked.connect(self.post_script_dialog)
        self.create_btn.clicked.connect(self.create_setup)
        self.add_driven_nodes_btn.clicked.connect(self.add_driven_render_nodes)
        self.default_selected_maps_btn.clicked.connect(self.default_maps_on_selected)

    def load_files_dialog(self, ext=techanim_creator_utils.TECH_MAP_EXT):
        """filedialog for selecting files to load. Generic

        Args:
            ext (str, optional): extension of desired filetype

        Returns:
            str: path of the selected file
        """
        abd_paths = []
        selected_files = ui_utils.QtFileDialog_files(ext, self)
        if not selected_files:
            return
        abd_paths = [os.path.abspath(x) for x in selected_files]
        self.ncloth_maps_edit.setText(str(abd_paths))
        return abd_paths

    def post_script_dialog(self):
        """load the post script file path into the UI

        Returns:
            str: selected python file
        """
        script_path = ui_utils.QtFileDialog_file("py", self)
        if not script_path:
            return
        script_path = os.path.abspath(script_path)
        self.post_script_edit.setText(script_path)
        return script_path

    def load_user_techanim_info(self):
        """load techanim info from a previous built setups

        Returns:
            n/a: zip
        """
        techanim_info = ast.literal_eval(self.user_techanim_info_edit.text() or "{}")
        if not techanim_info:
            return

        as_co = self.associate_control
        as_co.association_dict = techanim_info["render_sim"]
        render_model = self.render_geo_view.model()
        sim_model = self.sim_geo_view.model()
        render_model.clear()
        sim_model.clear()
        as_co.add_items(render_model, techanim_info["render_sim"].keys())
        as_co.add_items(sim_model, techanim_info["render_sim"].values())
        self.passive_edit.setText(str(techanim_info["rigid_nodes"]))

        setup_options = techanim_info.get("setup_options", {})
        if setup_options:
            for ui_key, value in setup_options.iteritems():
                ui_object = self.setup_options.get(ui_key)
                ui_object_type = type(ui_object)
                if ui_object_type == QtWidgets.QComboBox:
                    ui_object.setCurrentIndex(value)
                elif ui_object_type == QtWidgets.QLineEdit:
                    ui_object.setText(str(value))

        as_co.is_list_complete()

    def default_maps_on_selected(self):
        techanim_creator_utils.default_maps_selected()
        print("Maps have been defaulted!")

    def select_from_list(self, modelIndex):
        """Select the node from the listview in the scene

        Args:
            modelIndex (QModelIndex): To get data from
        """
        cmds.select(modelIndex.data())

    def add_selection(self, control, model):
        """Add selected nodes to the model for the UI

        Args:
            control (TYPE): Description
            model (TYPE): Description
        """
        items = self.get_selected()
        control.add_items(model, items)

    def add_passive_geo(self, items=None):
        """Add passive geo to the UI for rigid objects in nCloth

        Args:
            items (list, optional): of geo
        """
        if not items:
            items = self.get_selected()
        (safe_to_add,
         already_added) = self.associate_control.filter_dupicates(items)
        if already_added:
            msg = "Skipping duplicates! {}".format(already_added)
            print(msg)
        if safe_to_add:
            self.passive_edit.setText(str(safe_to_add))
        else:
            self.passive_edit.setText("")

    def get_selected(self):
        """Get selected maya nodes should they fit the filters

        Returns:
            list: of nodes selected in the scene
        """
        selected = cmds.ls(sl=True, type="transform")
        selected_with_mesh = []
        skipped = []
        for sel in selected:
            selChild = cmds.listRelatives(sel, shapes=True, type="mesh")
            if selChild:
                selected_with_mesh.append(sel)
            else:
                skipped.append(sel)
        if skipped:
            print("Following nodes with no shapes skipped: {}".format(skipped))
        return selected_with_mesh

    def update_render_label(self, modelIndex):
        """Update the label to display the number of added nodes

        Args:
            modelIndex (QtGui.modelIndex): to query the number of children
        """
        model = self.associate_control.modelA
        self.render_label.setText("Render Geo ({})".format(model.rowCount()))

    def update_geo_label(self, modelIndex):
        """Update the label to display the number of added nodes

        Args:
            modelIndex (QtGui.modelIndex): to query the number of children
        """
        model = self.associate_control.modelB
        self.sim_label.setText("Sim Geo ({})".format(model.rowCount()))

    def load_techanim_info_layout(self):
        """widget containing the area the user posts information for a previously
        created setup

        Returns:
            Qwidget: to be parented
        """
        group_widget = QtWidgets.QGroupBox("Load Techanim Info")
        # group_widget.setCheckable(True)
        layout = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel("Load Config:")
        self.user_techanim_info_edit = QtWidgets.QLineEdit()
        self.user_techanim_info_button = QtWidgets.QPushButton("Load")
        group_widget.setLayout(layout)
        layout.addWidget(label)
        layout.addWidget(self.user_techanim_info_edit)
        layout.addWidget(self.user_techanim_info_button)
        return group_widget

    def geo_selection_layout(self):
        """The render & sim qListview of the UI

        Returns:
            QtWidgets.QHBoxLayout: layout containing the widgets
            for this section.
        """
        selection_layout = QtWidgets.QHBoxLayout()
        render_layout = QtWidgets.QVBoxLayout()
        self.render_label = QtWidgets.QLabel("Render Geo (0)")
        self.render_geo_view = QtWidgets.QListView()
        self.render_geo_view.setObjectName("RenderGeoListView")
        self.render_geo_view.setToolTip("Select Geo, then its corresponding sim cage.")
        self.render_geo_view.setWhatsThis("Select Render Geo, then its corresponding sim cage.")
        self.render_geo_view.setCursor(QtCore.Qt.WhatsThisCursor)
        self.render_geo_add_btn = QtWidgets.QPushButton("Add Selected")
        self.render_geo_add_btn.setToolTip("Add selected geo. No duplicates.")
        self.render_geo_remove_btn = QtWidgets.QPushButton("Remove Selected")
        self.render_geo_remove_btn.setToolTip("Remove selected from List.")
        render_layout.addWidget(self.render_label)
        render_layout.addWidget(self.render_geo_view)
        render_layout.addWidget(self.render_geo_add_btn)
        render_layout.addWidget(self.render_geo_remove_btn)

        sim_layout = QtWidgets.QVBoxLayout()
        self.sim_label = QtWidgets.QLabel("Sim Geo (0)")
        self.sim_geo_view = QtWidgets.QListView()
        self.sim_geo_view.setToolTip("Select Render Geo, then sim geo.")
        self.sim_geo_view.setWhatsThis("Select Render Geo, then sim geo.")
        self.sim_geo_view.setObjectName("SimGeoListView")
        self.sim_geo_view.setCursor(QtCore.Qt.WhatsThisCursor)
        self.sim_geo_add_btn = QtWidgets.QPushButton("Add Selected")
        self.sim_geo_add_btn.setToolTip("Add selected geo. No duplicates.")
        self.sim_geo_remove_btn = QtWidgets.QPushButton("Remove Selected")
        self.sim_geo_remove_btn.setToolTip("Remove selected from List.")
        sim_layout.addWidget(self.sim_label)
        sim_layout.addWidget(self.sim_geo_view)
        sim_layout.addWidget(self.sim_geo_add_btn)
        sim_layout.addWidget(self.sim_geo_remove_btn)

        selection_layout.addLayout(render_layout)
        selection_layout.addLayout(sim_layout)

        return selection_layout

    def wrap_settings_layout(self):
        """layout containing the widgets for taking in wrap settings

        Returns:
            QtWidgets.QGroupBox : Similar to a layout, but allows for labeling
            of the section that is intuitive.
        """
        group_widget = QtWidgets.QGroupBox("Wrap Settings")
        # falloff -------------------------------------------------------------
        layout = QtWidgets.QVBoxLayout()
        layout_a = QtWidgets.QHBoxLayout()
        label_a = QtWidgets.QLabel("Fall Off Mode:")
        self.wrap_falloff_cb = QtWidgets.QComboBox()
        self.wrap_falloff_cb.addItems(["Volume", "Surface"])
        self.wrap_falloff_cb.setToolTip("Volume is faster than Surface.")
        layout_a.addWidget(label_a)
        layout_a.addWidget(self.wrap_falloff_cb)

        # Exclusive -----------------------------------------------------------
        layout_b = QtWidgets.QHBoxLayout()
        label_b = QtWidgets.QLabel("Exclusive Bind:")
        self.wrap_exclusive_cb = QtWidgets.QComboBox()
        self.wrap_exclusive_cb.addItems(["On", "Off"])
        self.wrap_exclusive_cb.setToolTip("On is faster than off.")
        layout_b.addWidget(label_b)
        layout_b.addWidget(self.wrap_exclusive_cb)

        layout.addLayout(layout_a)
        layout.addLayout(layout_b)
        group_widget.setLayout(layout)

        return group_widget

    def nCloth_settings_widget(self):
        """layout containing the widgets for taking in nCloth settings

        Returns:
            QtWidgets.QGroupBox : Similar to a layout, but allows for labeling
            of the section that is intuitive.
        """
        # creating the UI, model/view way
        group_widget = QtWidgets.QGroupBox("nCloth Settings")
        layout = QtWidgets.QVBoxLayout()

        layout_a = QtWidgets.QHBoxLayout()
        label_a = QtWidgets.QLabel("Passive Geo:")
        self.passive_edit = QtWidgets.QLineEdit()
        self.add_passive_btn = QtWidgets.QPushButton("Add Geo")
        layout_a.addWidget(label_a)
        layout_a.addWidget(self.passive_edit)
        layout_a.addWidget(self.add_passive_btn)

        layout.addLayout(layout_a)
        group_widget.setLayout(layout)

        return group_widget

    def create_setup_options_widget(self):
        group_widget = QtWidgets.QGroupBox("Create Settings")
        layout = QtWidgets.QVBoxLayout()
        # load maps -----------------------------------------------------------
        layout_a = QtWidgets.QHBoxLayout()
        label_a = QtWidgets.QLabel("nCloth Maps:")
        self.ncloth_maps_edit = QtWidgets.QLineEdit()
        self.ncloth_maps_button = QtWidgets.QPushButton("...")
        layout_a.addWidget(label_a)
        layout_a.addWidget(self.ncloth_maps_edit)
        layout_a.addWidget(self.ncloth_maps_button)

        # load post script ----------------------------------------------------
        layout_b = QtWidgets.QHBoxLayout()
        label_b = QtWidgets.QLabel("Post Script:    ")
        self.post_script_edit = QtWidgets.QLineEdit()
        self.post_script_button = QtWidgets.QPushButton("...")
        layout_b.addWidget(label_b)
        layout_b.addWidget(self.post_script_edit)
        layout_b.addWidget(self.post_script_button)

        layout.addLayout(layout_a)
        layout.addLayout(layout_b)

        self.create_btn = QtWidgets.QPushButton("Create Setup")
        self.create_btn.setToolTip("Create setup when ALL associations have been made.")
        self.create_btn.setEnabled(False)
        layout.addWidget(self.create_btn)
        group_widget.setLayout(layout)
        return group_widget

    def utils_layout(self):
        group_widget = QtWidgets.QGroupBox("Utils")
        # falloff -------------------------------------------------------------
        layout = QtWidgets.QVBoxLayout()
        layout_a = QtWidgets.QHBoxLayout()
        self.add_driven_nodes_btn = QtWidgets.QPushButton("Add Render Geo")
        self.add_driven_nodes_btn.setObjectName("AddRenderGeoButton")
        msg = "Select driven nodes and influence sim '{output_suffix}' object."
        msg = msg.format(**CONFIG)
        self.add_driven_nodes_btn.setWhatsThis(msg)
        self.add_driven_nodes_btn.setToolTip(msg)

        msg = "Default selected maps"
        self.default_selected_maps_btn = QtWidgets.QPushButton(msg)

        layout_a.addWidget(self.add_driven_nodes_btn)
        layout.addLayout(layout_a)
        layout.addWidget(self.default_selected_maps_btn)
        group_widget.setLayout(layout)
        return group_widget

    def create_setup(self):
        """Grab information from the ui that may have been change by the user
        and prepare for execution of the techanim_setup

        Returns:
            n/a: Zilch, nada, 何も
        """
        association_dict = self.associate_control.association_dict
        techanim_info = {}
        techanim_info["render_sim"] = copy.deepcopy(association_dict)
        if not techanim_info:
            return
        rigid_nodes = ast.literal_eval(self.passive_edit.text() or "[]")
        nClothMapsPaths = self.ncloth_maps_edit.text() or "[]"
        nClothMapsPaths = ast.literal_eval(nClothMapsPaths)
        setup_options = {
            "falloffMode": self.setup_options["falloffMode"].currentIndex(),
            "exclusiveBind": self.setup_options["exclusiveBind"].currentIndex(),
            "postScriptPath": self.post_script_edit.text(),
            "nClothMapsPaths": nClothMapsPaths
        }
        techanim_info = ast.literal_eval(self.user_techanim_info_edit.text()
                                         or "{}")
        add_key = techanim_creator_utils.ADDITIONAL_RENDER_OUTPUT_KEY
        addition_render_info = techanim_info.get(add_key, {})
        techanim_info["rigid_nodes"] = rigid_nodes
        techanim_info["setup_options"] = setup_options
        techanim_info[add_key] = addition_render_info
        print(techanim_info)
        techanim_creator_utils.create_setup(techanim_info,
                                            setup_options=setup_options)

    def add_driven_render_nodes(self):
        """Duplicate the selected nodes, parent them to the setup and drive
        them with a wrap deformer

        """
        selected = cmds.ls(sl=True)
        driven = selected[:-1]
        driver = selected[-1]
        if not driver.endswith(CONFIG["output_suffix"]):
            msg = "Driver must be selected last, and be an '{}' node."
            msg = msg.format(CONFIG["output_suffix"])
            ui_utils.genericWarning(self, msg)
            return
        falloffMode = WRAP_FALLOW_SETTINGS_DICT[self.wrap_falloff_cb.currentText().lower()]
        exclusiveBind = self.wrap_exclusive_cb.currentIndex() + 1
        techanim_creator_utils.add_driven_render_nodes(driver,
                                                       driven,
                                                       exclusiveBind=exclusiveBind,
                                                       falloffMode=falloffMode)

    def display_howto(self, howto_key):
        """Display the image over the widget

        Args:
            howto_key (str): key to the image
        """
        filepath = HOWTO_FILEPATH_DICT.get(howto_key)
        if filepath and os.path.exists(filepath):
            self.movie_screen.display_gif(filepath)
        else:
            print("Howto image not found: {}".format(filepath))

    def eventFilter(self, QObject, QEvent):
        """Catch the WhatsThis even on any widget and display its howto layer

        Args:
            QObject (QtCore.QObject): standard qobject
            QEvent (QtCore.QEvent): standard event that gets added

        Returns:
            Bool: original super call
        """
        if QEvent.type() == QtCore.QEvent.Type.WhatsThis:
            self.display_howto(QObject.objectName())
            QEvent.accept()

        return False

    def show(self):
        """Set focus to desired
        """
        super(TechAnimCreatorUI, self).show()
        self.setFocus()


# if __name__ == '__main__':
#     os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
#     qapp = QtWidgets.QApplication(sys.argv)
#     import maya.standalone
#     maya.standalone.initialize("Python")
#     qapp.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
#     qapp.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
#     tac_UI = show()
#     sys.exit(qapp.exec_())
