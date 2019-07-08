# -*- coding: utf-8 -*-
"""A UI to create, share, and organize presets. A "Preset" is a json file
of attribute: values information so it can be re-set on new nodes

TODO -
It would be nice to remove the QFilesystemModel. It is broken in PyQt5.9
If removed, it would allow more control of the recording of the indecies
If it is removed, one would need to find a way to keep the model up to date
with the filesystem.
Seperate this tool from the techanim module
Remove WhatIsThis "?" from the window

Attributes:
    TOOLTIP_TEMPLATE (str): To display to the user
    WINDOW_TITLE (str): Title of the UI
"""

from __future__ import division
from __future__ import generators
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

__author__ = "Rafael Villar"
__license__ = "MIT"
__version__ = "1.0.0"
__email__ = "rav@ravrigs.com"
__credits__ = ["Bae Jaechul", "www.studioanima.co.jp/en/"]

import os
import getpass

try:
    from Qt import QtWidgets, QtGui, QtCore
except Exception:
    from PySide2 import QtWidgets, QtGui, QtCore

import maya.cmds as cmds

from techanim_flow import ui_utils
from techanim_flow import preset_share_utils
from techanim_flow import techanim_creator_utils

reload(techanim_creator_utils)

# =============================================================================
# constants
# =============================================================================
WINDOW_TITLE = "Preset Share"

TOOLTIP_TEMPLATE = \
    """
comment: {comment}
User: {user}
origin scene: {origin_scene}

"""
CONFIG = techanim_creator_utils.CONFIG
os.environ["PRESET_SHARE_BASE_DIR"] = CONFIG["PRESET_SHARE_BASE_DIR"]


def show():
    """To launch the ui and not get the same instance

    Returns:
        DistributeUI: instance

    Args:
        *args: Description
    """
    # global TECH_CREATOR_UI
    try:
        ui_utils.close_existing(class_name="PresetShareUI")
    except Exception:
        pass
    maya_window = ui_utils.mainWindow() or None
    PS_UI = PresetShareUI(parent=maya_window)
    PS_UI.show()
    return PS_UI


# =============================================================================
# UI classes
# =============================================================================


class NameAndDescribePresetUI(QtWidgets.QDialog):

    def __init__(self,
                 ui_name,
                 nodetype_display=None,
                 auto_name=None,
                 auto_comment=None,
                 completer_list=None,
                 parent=None):
        """Pop up window to gather name and comment from user about the preset

        Args:
            ui_name (str): name to give the ui
            auto_name (str, optional): should a name be already set
            auto_comment (str, optional): should a comment already be filled
            completer_list (list, optional): list of names for the completer
            parent (QtWidget, optional): Window to parent over
        """
        super(NameAndDescribePresetUI, self).__init__(parent=parent)
        self.setWindowTitle(ui_name)
        mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(mainLayout)
        self.result = []
        #  --------------------------------------------------------------------
        if nodetype_display:
            create_layout = QtWidgets.QVBoxLayout()
            msg = "Creating a preset for:"
            creating_label = QtWidgets.QLabel(msg)
            nodetype_label = QtWidgets.QLabel(nodetype_display)
            font = nodetype_label.font()
            font.setBold(True)
            nodetype_label.setFont(font)
            create_layout.addWidget(creating_label)
            create_layout.addWidget(nodetype_label)
            mainLayout.addLayout(create_layout)
        selectionLayout = QtWidgets.QHBoxLayout()
        selectionLabel = QtWidgets.QLabel("Give preset name:")
        self.preset_name_edit = QtWidgets.QLineEdit()
        self.preset_name_edit.setPlaceholderText("name")
        val = QtGui.QRegExpValidator(QtCore.QRegExp("[A-Za-z]+"))
        self.preset_name_edit.setValidator(val)
        if auto_name:
            self.preset_name_edit.setText(auto_name)

        if completer_list:
            com = QtWidgets.QCompleter(completer_list)
            self.preset_name_edit.setCompleter(com)

        selectionLayout.addWidget(selectionLabel)
        selectionLayout.addWidget(self.preset_name_edit)
        mainLayout.addLayout(selectionLayout)
        #  --------------------------------------------------------------------
        self.comment_widget = QtWidgets.QTextEdit()
        self.comment_widget.setPlaceholderText("Details on the preset.")
        mainLayout.addWidget(self.comment_widget)
        if auto_comment:
            self.comment_widget.setText(auto_comment)

        #  --------------------------------------------------------------------
        # buttonLayout = QtWidgets.QHBoxLayout()
        self.okButton = QtWidgets.QPushButton("Ok")
        self.okButton.clicked.connect(self.onOK)
        mainLayout.addWidget(self.okButton)

    def onOK(self):
        """collect data when the user hits ok

        Returns:
            list: of collected info
        """
        if self.preset_name_edit.text() == "":
            cmds.warning("You need to provide a name!")
            return
        if self.comment_widget.toPlainText() == "":
            cmds.warning("You need to provide a Description")
            return
        self.result.extend([self.preset_name_edit.text(),
                           self.comment_widget.toPlainText()])
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
        super(NameAndDescribePresetUI, self).exec_()
        return self.result


class PresetShareUI(QtWidgets.QDialog):

    """A tool to create, delete, share presets in a folder structure

    Attributes:
        apply_preset_btn (QPushbutton): apply preset widget
        collected_dir_info (dict): information collected from the QFilesystem
        because its trash and doesnt function properly
        completer (QCompleter): searching completion, limited due to QFilesystemModel
        create_preset_btn (QPushButton): Widget that triggers creation
        file_manager (QFileSystemModel): garbage
        file_view (QTreeView): Showing filesystem
        mainLayout (QVBoxLayout): umm, vanilla ice
        root_model_index (QModelIndex): To set the QTreeView
        parent (QtWidget): maya main window wrapped
        preset_share_dir (str): Directory where the preset files are stored
        pubMenu (QMenu): CustomContext Menu
        search_widget (QLineEdit): search area to find folders
        skip_other_users (bool): Should the qCompleter for search crawl other
        users, this is probably slow and messy to look at.
        text_view (QTextEdit): Display info to the user
    """

    def __init__(self, parent=None):
        super(PresetShareUI, self).__init__(parent=parent)
        # window prep ---------------------------------------------------------
        self.parent = parent
        self.setWindowTitle(WINDOW_TITLE)
        self.setObjectName(self.__class__.__name__)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        minflag = QtCore.Qt.WindowMinimizeButtonHint
        self.setWindowFlags(self.windowFlags() | minflag)
        self.setMinimumWidth(350)
        self.preset_share_dir = preset_share_utils.get_base_dir()
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.mainLayout)

        # logic variables -----------------------------------------------------
        self._remember_dir_var = "{}lastpath".format(self.__class__.__name__)
        self.skip_other_users = True
        self.collected_dir_info = {}
        self.view_expanded_state_info = {}
        self._state_gathered = False

        # file system crawl and display ---------------------------------------
        self.search_widget = QtWidgets.QLineEdit()
        self.search_widget.setPlaceholderText("Search")

        self.file_manager = QtWidgets.QFileSystemModel()
        ext_filters = ["*.{}".format(preset_share_utils.PRESET_EXT)]
        self.file_manager.setNameFilters(ext_filters)
        self.file_manager.rowsInserted.connect(self.manual_tracking)
        self.file_manager.columnsInserted.connect(self.manual_tracking)
        self.file_manager.directoryLoaded.connect(self.loadedPath)
        self.root_model_index = self.file_manager.setRootPath(self.preset_share_dir)

        self.file_view = QtWidgets.QTreeView()
        self.file_view.setModel(self.file_manager)
        self.file_view.setRootIndex(self.root_model_index)
        self.file_view.hideColumn(1)
        self.file_view.hideColumn(2)
        self.file_view.clicked.connect(self.preset_selected)
        self.file_view.header().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        # self.file_view.header().setStretchLastSection(True)
        self.file_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.file_view.customContextMenuRequested.connect(self.create_context_menu)

        # Arbitrarily setting this now, as it gets set again with signals -----
        self.set_search_completer()

        self.text_view = QtWidgets.QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setMaximumHeight(100)

        self.apply_preset_btn = QtWidgets.QPushButton("Apply Preset")
        self.apply_preset_btn.setToolTip("Select Node of same type.")
        self.apply_preset_btn.setEnabled(False)
        self.apply_preset_btn.clicked.connect(self.apply_preset)

        self.create_preset_btn = QtWidgets.QPushButton("Create Preset")
        self.create_preset_btn.setToolTip("Select Node in Maya")
        self.create_preset_btn.clicked.connect(self.create_preset)

        self.mainLayout.addWidget(self.search_widget)
        self.mainLayout.addWidget(self.file_view)
        self.mainLayout.addWidget(self.text_view)
        self.mainLayout.addWidget(self.apply_preset_btn)
        self.mainLayout.addWidget(self.create_preset_btn)

    def create_context_menu(self, QPos):
        """Check if there is a selection make in the View before making window

        Args:
            QPos (QPoint): location of right click request

        Returns:
            n/a: the second season of Firefly
        """
        modelIndex = self.file_view.selectionModel().currentIndex()
        if not modelIndex:
            return
        selected_path = self.file_manager.filePath(modelIndex)
        self.custom_menu(modelIndex, selected_path, QPos)

    def custom_menu(self, modelIndex, selected_path, QPos):
        """Create menu at point requested

        Args:
            QPos (QPoint): location of the request, that
            needs to get mapped to the window
        """
        if self.file_manager.type(modelIndex) != "preset File":
            return
        self.pubMenu = QtWidgets.QMenu()
        parentPosition = self.file_view.viewport().mapToGlobal(QtCore.QPoint(0, 0))
        menu_item_01 = self.pubMenu.addAction("Publish Preset")
        menu_item_01.setToolTip("Publish Preset")
        menu_item_01.triggered.connect(self.publish_preset)

        user_dir = preset_share_utils.get_user_dir(getpass.getuser())
        user_dir = user_dir.replace("\\", "/")
        if preset_share_utils.in_directory(selected_path, user_dir):
            menu_item_02 = self.pubMenu.addAction("Delete Preset")
            self.pubMenu.insertSeparator(menu_item_02)
            menu_item_02.triggered.connect(self.delete_selected_preset)

        self.pubMenu.move(parentPosition + QPos)
        self.pubMenu.show()

    def preset_selected(self, item):
        """Check the item selected, is it a file or folder

        Args:
            item (QModelIndex): to query for path
        """
        filepath = self.file_manager.filePath(item)
        self.remember_dir(filepath)
        if self.file_manager.type(item) == "preset File":
            self.load_info(item)
            self.apply_preset_btn.setEnabled(True)
        else:
            self.text_view.setText("")
            self.apply_preset_btn.setEnabled(False)

    # Inability to record and reimplement the collapse state of the view
    # def _gather_view_collapsed_state(self):
    #     """Record the exapnded state so we can set it back at any time.
    #     """
    #     self._state_gathered = True
    #     for path, modelIndex in self.collected_dir_info.iteritems():
    #         exState = self.file_view.isExpanded(modelIndex)
    #         print(path, exState)
    #         self.view_expanded_state_info[path] = exState

    # def _set_gathered_collapse_state(self):
    #     if not self._state_gathered:
    #         print(self._state_gathered)
    #         return
    #     for path, exState in self.view_expanded_state_info.iteritems():
    #         if path in self.collected_dir_info:
    #             print("derp")
    #             modelIndex = self.collected_dir_info[path]
    #             if exState:
    #                 self.temp_shit = []
    #                 print(path, exState, 1)
    #                 self.file_view.expand(modelIndex)
    #                 self.file_view.setExpanded(modelIndex, True)
    #                 self.temp_shit.append(modelIndex)
    #             else:
    #                 self.file_view.collapse(modelIndex)
    #                 self.file_view.setExpanded(modelIndex, False)
    #     self._state_gathered = False

    def set_search_completer(self):
        """Set the QCompleter for the search edit.
        TODO Check if there is a way to update the contents of completer
        rather recreate new one every time. seems costly
        """
        folders = self.collected_dir_info.keys()
        base_folders = []
        for x in folders:
            tmp = os.path.abspath(x).replace(self.preset_share_dir, "")
            tmp = tmp.strip("\\")
            base_folders.append(tmp)

        self.completer = QtWidgets.QCompleter(base_folders)
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.completer.setFilterMode(QtCore.Qt.MatchContains)
        self.completer.activated.connect(self.filter_view)
        self.search_widget.setCompleter(self.completer)

    def load_info(self, item):
        """Based on selection, load info from preset, json, or not

        Args:
            item (TYPE): Description
        """
        filepath = self.file_manager.filePath(item)
        preset_info = preset_share_utils._importData(filepath)
        if preset_info:
            msg = TOOLTIP_TEMPLATE.format(**preset_info)
        else:
            msg = "No information found."

        self.text_view.setText(msg)

    def filter_view(self, text):
        """Selects the item when the user completes the qcompleter

        Args:
            text (str): from the search edit
        """
        fullpath = os.path.join(self.preset_share_dir, text)
        fullpath = fullpath.replace("\\", "/")
        modelIndex = self.collected_dir_info.get(fullpath)
        if modelIndex:
            self.file_view.scrollTo(modelIndex)
            flags = QtCore.QItemSelectionModel.Rows | QtCore.QItemSelectionModel.ClearAndSelect
            self.file_view.selectionModel().select(modelIndex, flags)

    def manual_tracking(self, *args):
        """The QFileSystemModel is apparently broken, so we need to do our own
        tracking.

        Args:
            *args: QModelIndex and other garbage

        """
        modelIndex = QtCore.QPersistentModelIndex(args[0])
        path = self.file_manager.filePath(modelIndex)
        if preset_share_utils.in_directory(path, self.preset_share_dir):
            if self.skip_other_users:
                userPath = preset_share_utils.get_user_dir(getpass.getuser())
                publish_path = preset_share_utils.get_publish_dir()
                if (preset_share_utils.in_directory(path, userPath) or
                        preset_share_utils.in_directory(path, publish_path)):
                    self.collected_dir_info[path] = modelIndex
                    self.set_search_completer()
            else:
                self.collected_dir_info[path] = modelIndex
                self.set_search_completer()

    def loadedPath(self, *args):
        """For loading the QTreeView with the folders. This could be costly if
        the folder structure werent so shallow

        Args:
            *args: Signal garbage
        """
        self.file_view.expandAll()
        self.file_view.collapseAll()
        self.set_remembered_dir()

    def set_remembered_dir(self):
        """Set the last selected or loaded preset to be remembered if the
        UI is relaunched.
        """
        modelIndex = None
        if cmds.optionVar(exists=self._remember_dir_var):
            last_path = cmds.optionVar(q=self._remember_dir_var)
            if last_path in self.collected_dir_info:
                modelIndex = self.collected_dir_info.get(last_path)
        else:
            sel = cmds.ls(sl=True)
            if sel:
                nodetype = cmds.nodeType(sel)
                folder = "{}/{}".format(getpass.getuser(), nodetype)
                for k, y in self.collected_dir_info.iteritems():
                    if k.endswith(folder):
                        modelIndex = y
                        break

        if modelIndex:
            self.file_view.scrollTo(modelIndex)
            flags = QtCore.QItemSelectionModel.Rows | QtCore.QItemSelectionModel.ClearAndSelect
            self.file_view.selectionModel().select(modelIndex, flags)

    def remember_dir(self, path):
        """Remember the Titans, with Denzel Washinton.

        Args:
            path (str): Save the path in a Maya optionVar
        """
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        cmds.optionVar(sv=[self._remember_dir_var, path])

    # =========================================================================
    # applying/creating presets
    # =========================================================================
    def apply_preset(self):
        """Apply the selected preset to the selected node, ensuring the dest
        node is of the same type.
        """
        modelIndex = self.file_view.selectionModel().currentIndex()
        scene_nodes = cmds.ls(sl=True)
        if not modelIndex or not scene_nodes:
            print("Select desired preset and a node in Maya.")
            return
        selected_path = self.file_manager.filePath(modelIndex)
        preset_info = preset_share_utils._importData(selected_path)
        failed_nodes = []
        for node in scene_nodes:
            if cmds.nodeType(node) != preset_info["nodetype"]:
                failed_nodes.append(node)
                continue
            preset_share_utils.apply_preset(preset_info, node)

        if failed_nodes:
            msg = "Failed to apply preset! Ensure same node type. {}".format(failed_nodes)
            print(msg)

    def create_preset(self):
        """Create Preset from the selected node in Maya
        """
        # self._gather_view_collapsed_state()
        scene_node = cmds.ls(sl=True)
        if not scene_node:
            cmds.warning("Select Node to create preset from.")
            return
        user = getpass.getuser()
        nodetype = cmds.nodeType(scene_node[0])
        completer_list = preset_share_utils.get_all_user_descriptors(user,
                                                                     nodetype)
        nodetype_display = "{}:{}".format(scene_node[0], nodetype.capitalize())
        results = NameAndDescribePresetUI("Name Preset",
                                          nodetype_display=nodetype_display,
                                          completer_list=completer_list,
                                          parent=self).exec_()
        if not results:
            return
        preset_share_utils.save_preset_for_node(scene_node[0],
                                                results[1],
                                                results[0],
                                                user=getpass.getuser())
        # self._set_gathered_collapse_state()

    def publish_preset(self):
        """Load the selected preset, ask user if they would like to add new
        comment or name and then save in publish location.
        """
        # self._gather_view_collapsed_state()
        modelIndex = self.file_view.selectionModel().currentIndex()
        selected_path = self.file_manager.filePath(modelIndex)
        desciptor = preset_share_utils.split_name(selected_path)[1]
        preset_info = preset_share_utils._importData(selected_path)
        nodetype = preset_info["nodetype"]
        comment = preset_info["comment"]
        descri_list = preset_share_utils.get_all_publish_descriptors(nodetype)
        results = NameAndDescribePresetUI("Name Preset",
                                          auto_name=desciptor,
                                          auto_comment=comment,
                                          completer_list=descri_list,
                                          parent=self).exec_()
        if not results:
            return
        preset_share_utils.publish_preset(selected_path,
                                          new_comment=results[1],
                                          new_description=results[0])
        # self._set_gathered_collapse_state()

    def delete_selected_preset(self, modelIndex=None):
        """Use the QFileSystemModel to delete the file because its watching the
        directories and we do not want to anger the gods.

        Args:
            modelIndex (QModelIndex, optional): item to be deleted, if not
            provided get currently selected
        """
        # self._gather_view_collapsed_state()
        if not modelIndex:
            modelIndex = self.file_view.selectionModel().currentIndex()
        if not modelIndex:
            return
        # selected_path = self.file_manager.filePath(modelIndex)
        # modelIndex = self.collected_dir_info.pop(selected_path)
        self.file_manager.remove(modelIndex)
        # self._set_gathered_collapse_state()
        self.set_remembered_dir()

    # =========================================================================
    # overrides
    # =========================================================================

    def closeEvent(self, closeEvent):
        """Making sure we delete that QFileSystemModel because it watching the
        dirs and I dont want to hang up Windows.

        Args:
            closeEvent (QEvent):
        """
        # print("Cleaning up...")
        try:
            self.file_manager.deleteLater()
        except Exception:
            self.deleteLater()

        try:
            super(PresetShareUI, self).closeEvent(closeEvent)
        except TypeError:
            self.deleteLater()
