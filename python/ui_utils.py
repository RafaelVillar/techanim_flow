# -*- coding: utf-8 -*-
# Standard
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import generators
from __future__ import division

import maya.OpenMayaUI as omui

from shiboken2 import wrapInstance

try:
    from Qt import QtWidgets, QtGui, QtCore
except Exception:
    from PySide2 import QtWidgets, QtGui, QtCore


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
