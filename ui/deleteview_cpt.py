#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad
from __future__ import (
    unicode_literals, absolute_import, division, print_function)

from PyQt4.QtGui import (QVBoxLayout, QHBoxLayout, QGridLayout, QDialog)
from PyQt4.QtCore import Qt

from Common.ui.common import FWidget, FPageTitle, Button, FLabel


class DeleteViewWidget(QDialog, FWidget):

    def __init__(self, table_p, obj, parent, *args, **kwargs):
        QDialog.__init__(self, parent, *args, **kwargs)

        self.setWindowTitle(u"Confirmation de le suppression")
        self.title = FPageTitle(u"Voulez vous vraiment le supprimer?")
        self.obj = obj
        self.table_p = table_p
        self.parent = parent
        # self.title.setAlignment(Qt.AlignHCenter)
        title_hbox = QHBoxLayout()
        title_hbox.addWidget(self.title)
        report_hbox = QGridLayout()

        report_hbox.addWidget(FLabel(obj.display_name()), 0, 0)
        # delete and cancel hbox
        Button_hbox = QHBoxLayout()

        # Delete Button widget.
        delete_but = Button(u"Supprimer")
        Button_hbox.addWidget(delete_but)
        delete_but.clicked.connect(self.delete)
        # Cancel Button widget.
        cancel_but = Button(u"Annuler")
        Button_hbox.addWidget(cancel_but)
        cancel_but.clicked.connect(self.cancel)

        # Create the QVBoxLayout contenaire.
        vbox = QVBoxLayout()
        vbox.addLayout(title_hbox)
        vbox.addLayout(report_hbox)
        vbox.addLayout(Button_hbox)
        self.setLayout(vbox)

    def cancel(self):
        self.close()
        return False

    def delete(self):
        self.obj.delete_data()
        self.cancel()
        self.table_p.refresh_()
        self.parent.Notify("le rapport à été bien supprimé", "error")
