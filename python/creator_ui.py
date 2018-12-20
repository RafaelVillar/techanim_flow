# -*- coding: utf-8 -*-
# Standard
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import generators
from __future__ import division

import os
import ast
import sys
import copy

from functools import partial

import maya.cmds as cmds
import maya.OpenMayaUI as omui

from shiboken2 import wrapInstance

try:
    from Qt import QtWidgets, QtGui, QtCore
except Exception:
    from PySide2 import QtWidgets, QtGui, QtCore

import creator_utils
reload(creator_utils)
from creator_utils import CONFIG

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
DIR_PATH = os.path.dirname(__file__)
WINDOW_TITLE = "TechAnim Creator"
HOWTO_FILEPATH_DICT = CONFIG.get("HOWTO_FILEPATH_DICT", {})

for _key, _path in HOWTO_FILEPATH_DICT.iteritems():
    HOWTO_FILEPATH_DICT[_key] = os.path.join(DIR_PATH, os.path.normpath(_path))


def mainWindow():
    """useless, but should get maya main window

    Returns:
        QMainWindow: of maya main window
    """
    mainWindowPtr = omui.MQtUtil.mainWindow()
    if not mainWindowPtr:
        return None
    mayaMainWindow = wrapInstance(long(mainWindowPtr), QtWidgets.QMainWindow)
    return mayaMainWindow


def get_top_level_widgets(class_name=None, object_name=None):
    """
    Get existing widgets for a given class name

    Args:
        class_name (str): Name of class to search top level widgets for
        object_name (str): Qt object name

    Returns:
        List of QWidgets
    """
    matches = []

    # Find top level widgets matching class name
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            # Matching class
            if class_name and widget.metaObject().className() == class_name:
                matches.append(widget)
            # Matching object name
            elif object_name and widget.objectName() == object_name:
                matches.append(widget)
        # Error: 'PySide2.QtWidgets.QListWidgetItem' object
        #        has no attribute 'inherits'
        except AttributeError:
            continue
        # Print unhandled to the shell
        except Exception as e:
            print(e)

    return matches


def close_existing(class_name=None, object_name=None):
    """
    Close and delete any existing windows of class_name

    Args:
        class_name (str): QtWidget class name
        object_name (str): Qt object name

    Returns: None
    """
    for widget in get_top_level_widgets(class_name, object_name):
        # Close
        widget.close()
        # Delete
        widget.deleteLater()


def show(dockable=True, newSceneCallBack=True, *args):
    """To launch the ui and not get the same instance

    Returns:
        DistributeUI: instance

    Args:
        *args: Description
    """
    # global TECH_CREATOR_UI
    try:
        close_existing(class_name="TechAnimCreatorUI")
    except Exception:
        pass
    maya_window = mainWindow() or None
    TECH_CREATOR_UI = TechAnimCreatorUI(parent=maya_window)
    TECH_CREATOR_UI.show()
    TECH_CREATOR_UI.adjustSize()
    return TECH_CREATOR_UI


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
        self.__models = {self.modelA: self.modelB, self.modelB: self.modelA}
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
        self.setObjectName(WINDOW_TITLE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setWindowFlags(self.windowFlags())

        # self.setMinimumWidth(400)
        # self.resize(QtCore.QSize(450, 500))

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)

        self.mainLayout.addLayout(self.geo_selection_layout())
        self.mainLayout.addWidget(self.wrap_settings_layout())
        self.mainLayout.addWidget(self.nCloth_settings())
        self.create_btn = QtWidgets.QPushButton("Create Setup")
        self.create_btn.setEnabled(False)
        self.mainLayout.addWidget(self.create_btn)
        self.associate_control = AssociateSelectionControl(self.render_geo_view,
                                                           self.sim_geo_view)

        # attach signals and filters ------------------------------------------
        self.create_signal_connections()
        self.render_geo_view.installEventFilter(self)
        self.sim_geo_view.installEventFilter(self)

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
        self.create_btn.clicked.connect(self.create_setup)

    def select_from_list(self, modelIndex):
        """Select maya nodes from the provided modelIndex

        Args:
            modelIndex (TYPE): Description
        """
        cmds.select(modelIndex.data())

    def add_selection(self, control, model):
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

        Args:
            modelIndex (TYPE): Description
        """
        model = self.associate_control.modelB
        self.sim_label.setText("Sim Geo ({})".format(model.rowCount()))

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
        self.render_geo_view.setWhatsThis("Select Render Geo, then its corresponding sim cage.")
        self.render_geo_add_btn = QtWidgets.QPushButton("Add Selected")
        self.render_geo_remove_btn = QtWidgets.QPushButton("Remove Selected")
        render_layout.addWidget(self.render_label)
        render_layout.addWidget(self.render_geo_view)
        render_layout.addWidget(self.render_geo_add_btn)
        render_layout.addWidget(self.render_geo_remove_btn)

        sim_layout = QtWidgets.QVBoxLayout()
        self.sim_label = QtWidgets.QLabel("Sim Geo (0)")
        self.sim_geo_view = QtWidgets.QListView()
        self.sim_geo_view.setWhatsThis("Select Render Geo, then sim geo.")
        self.sim_geo_view.setObjectName("SimGeoListView")
        self.sim_geo_add_btn = QtWidgets.QPushButton("Add Selected")
        self.sim_geo_remove_btn = QtWidgets.QPushButton("Remove Selected")
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
        group_wdidget = QtWidgets.QGroupBox("Wrap Settings")
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
        group_wdidget.setLayout(layout)

        return group_wdidget

    def nCloth_settings(self):
        """layout containing the widgets for taking in nCloth settings

        Returns:
            QtWidgets.QGroupBox : Similar to a layout, but allows for labeling
            of the section that is intuitive.
        """
        # creating the UI, model/view way
        group_wdidget = QtWidgets.QGroupBox("nCloth Settings")
        layout = QtWidgets.QVBoxLayout()

        layout_a = QtWidgets.QHBoxLayout()
        label_a = QtWidgets.QLabel("Passive Geo:")
        self.passive_edit = QtWidgets.QLineEdit()
        self.add_passive_btn = QtWidgets.QPushButton("Add Geo")
        layout_a.addWidget(label_a)
        layout_a.addWidget(self.passive_edit)
        layout_a.addWidget(self.add_passive_btn)

        layout.addLayout(layout_a)
        group_wdidget.setLayout(layout)

        return group_wdidget

    def create_setup(self):
        """Grab information from the ui that may have been change by the user
        and prepare for execution of the techanim_setup

        Returns:
            n/a: Zilch, nada, 何も
        """
        association_dict = self.associate_control.association_dict
        tmp = {}
        tmp["render_sim"] = copy.deepcopy(association_dict)
        render_sim_association_dict = tmp
        if not tmp:
            return
        rigid_nodes = ast.literal_eval(self.passive_edit.text() or "[]")
        tmp["rigid_nodes"] = rigid_nodes
        setup_options = {
            "fallOffMode": str(self.wrap_falloff_cb.currentText()),
            "exclusiveBind": self.wrap_exclusive_cb.currentIndex() + 1
        }
        print(association_dict)
        print(render_sim_association_dict)
        print(setup_options)
        creator_utils.create_setup(render_sim_association_dict,
                                   setup_options=setup_options)

    def display_howto(self, howto_key):
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

    def resizeEventee(self, event):
        '''Resizing the howto layer, otherwise pass through
        '''
        size = self.size()
        self.movie_screen.resize(size)
        return super(TechAnimCreatorUI, self).resizeEvent(event)


if __name__ == '__main__':
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    qapp = QtWidgets.QApplication(sys.argv)
    qapp.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    qapp.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    tac_UI = show()
    sys.exit(qapp.exec_())
