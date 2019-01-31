# -*- coding: utf-8 -*-
"""generic UI tools to be used by the creator/manager
"""
# Standard
from __future__ import division
from __future__ import generators
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import maya.OpenMayaUI as omui

from shiboken2 import wrapInstance

try:
    from Qt import QtWidgets
except Exception:
    from PySide2 import QtWidgets


def genericWarning(parent, warningText):
    """generic prompt warning with the provided text

    Args:
        parent (QWidget): Qwidget to be parented under
        warningText (str): information to display to the user

    Returns:
        QtCore.Response: of what the user chose. For warnings
    """
    selWarning = QtWidgets.QMessageBox(parent)
    selWarning.setText(warningText)
    results = selWarning.exec_()
    return results


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
        del(widget)


class GenericSelectionUI(QtWidgets.QDialog):

    """Allow the user to select which attrs will drive the rbf nodes in a setup

    Attributes:
        drivenListWidget (QListWidget): widget to display attrs to drive setup
        okButton (QPushButton): BUTTON
        result (list): of selected attrs from listWidget
        setupField (bool)): Should the setup lineEdit widget be displayed
        setupLineEdit (QLineEdit): name selected by user
    """

    def __init__(self, ui_name, itemList, parent=None):
        """setup the UI widgets

        Args:
            itemList (list): attrs to be displayed on the list
            parent (QWidget, optional): widget to parent this to
        """
        super(GenericSelectionUI, self).__init__(parent=parent)
        self.setWindowTitle(ui_name)
        mainLayout = QtWidgets.QVBoxLayout()
        self.setLayout(mainLayout)
        self.result = []
        #  --------------------------------------------------------------------
        selectionLayout = QtWidgets.QVBoxLayout()
        selectionLabel = QtWidgets.QLabel("Select Target Namespace")
        self.drivenListWidget = QtWidgets.QListWidget()
        self.drivenListWidget.addItems(itemList)
        selectionLayout.addWidget(selectionLabel)
        selectionLayout.addWidget(self.drivenListWidget)
        mainLayout.addLayout(selectionLayout)
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
        selected_text_results = []
        selected_namespace_items = self.drivenListWidget.selectedItems()
        if not selected_namespace_items:
            genericWarning(self, "Select a namespaces!")
            return
        for item in selected_namespace_items:
            selected_text_results.append(item.text())
        self.result.extend(selected_text_results)
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
