# -*- coding: utf-8 -*-

##########################################################################
#                                                                        #
#  csv-import: an Eddy plugin to import description from csv files.      #
#  Copyright (C) 2020 Manuel Namici                                      #
#                                                                        #
#  ####################################################################  #
#                                                                        #
#  This program is free software: you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation, either version 3 of the License, or     #
#  (at your option) any later version.                                   #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
#  GNU General Public License for more details.                          #
#                                                                        #
#  You should have received a copy of the GNU General Public License     #
#  along with this program. If not, see <http://www.gnu.org/licenses/>.  #
#                                                                        #
##########################################################################


import csv
import textwrap

from PyQt5 import (
    QtCore,
    QtWidgets,
)
from eddy.core.commands.nodes import CommandNodeSetMeta
from eddy.core.datatypes.system import File
from eddy.core.functions.misc import first
from eddy.core.functions.path import expandPath
from eddy.core.plugin import AbstractPlugin
from eddy.core.project import K_DESCRIPTION, K_DESCRIPTION_STATUS
from eddy.ui.progress import BusyProgressDialog


class CsvImportPlugin(AbstractPlugin):
    """
    This plugin provides the ability to import and merge project
    descriptions from a csv file.
    """
    sgnChanged = QtCore.pyqtSignal(float)

    def __init__(self, spec, session):
        """
        Initialize the plugin.
        :type spec: PluginSpec
        :type session: session
        """
        super().__init__(spec, session)

    #############################################
    #   SLOTS
    #################################

    @QtCore.pyqtSlot()
    def doImportDescriptions(self):
        """
        Start the CSV import process.
        """
        # SELECT CSV FILE VIA FILE DIALOG
        dialog = QtWidgets.QFileDialog(self.session)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptOpen)
        dialog.setDirectory(expandPath('~'))
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        dialog.setViewMode(QtWidgets.QFileDialog.Detail)
        dialog.setNameFilters([File.Csv.value])
        if not dialog.exec_():
            return
        selected = expandPath(first(dialog.selectedFiles()))
        self.debug('Importing descriptions from file: {}'.format(selected))
        reader = csv.reader(selected, dialect='excel', quoting=csv.QUOTE_ALL, quotechar='"')

        # PARSE CSV AND GENERATE COMMANDS
        commands = []
        for row in reader:
            try:
                predicate, description = row[:2]

                # GET NODE CORRESPONDING TO PREDICATE
                for node in self.project.predicates(name=predicate):
                    undo = self.project.meta(node.type(), node.text())
                    redo = undo.copy()
                    redo[K_DESCRIPTION] = description
                    undo[K_DESCRIPTION_STATUS] = undo.get(K_DESCRIPTION_STATUS, '')
                    redo[K_DESCRIPTION_STATUS] = undo.get(K_DESCRIPTION_STATUS, '') # TODO: ADD STATUS COLUMN TO CSV

                    # TODO: there is no conflict handler at the moment,
                    # We need to provide here an interface for the user to
                    # merge the current and imported description
                    if redo != undo:
                        commands.append(CommandNodeSetMeta(self.project, node.type(), node.text(), undo, redo))
            except Exception as e:
                self.session.addNotification(textwrap.dedent("""
                <b><font color="#7E0B17">ERROR</font></b>: Could not complete description import,
                please see the log for details.
                """))
                return

        # APPLY CHANGES
        with BusyProgressDialog("Applying changes..."):
            self.session.undostack.beginMacro('edit {0} description'.format(self.node.name))
            for command in commands:
                self.session.undostack.push(command)
            self.session.undostack.endMacro()

    #############################################
    #   INTERFACE
    #################################

    #############################################
    #   HOOKS
    #################################

    def dispose(self):
        """
        Executed whenever the plugin is going to be destroyed.
        """
        # UNINSTALL THE MENU ACTION
        self.debug('Uninstalling action from menu')
        self.session.menu('tools').removeAction(self.action('csv-import'))

    def start(self):
        """
        Perform initialization tasks for the plugin.
        """
        # INITIALIZE ACTIONS
        self.debug('Creating csv-import actions')
        # noinspection PyArgumentList
        self.addAction(QtWidgets.QAction(
            'Import CSV', parent=self.session, objectName='csv-import',
            triggered=self.doImportDescriptions))

        # CONFIGURE SIGNALS/SLOTS
        self.debug('Configuring plugin signals/slots')

        # ADD SESSION MENU ACTIONS
        self.debug('Installing menu actions')
        self.session.menu('tools').addSeparator()
        self.session.menu('tools').addAction(self.action('csv-import'))
