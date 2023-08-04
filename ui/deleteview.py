#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad
from __future__ import (
    unicode_literals, absolute_import, division, print_function)

from PyQt4.QtGui import (QVBoxLayout, QHBoxLayout, QGridLayout, QDialog)


from Common.ui.common import FWidget, FPageTitle, Button, FLabel


class DeleteViewWidget(QDialog, FWidget):

    def __init__(self, table_p, obj, parent, *args, **kwargs):
        QDialog.__init__(self, parent, *args, **kwargs)

        self.setWindowTitle("Confirmation de suppression")
        self.title = FPageTitle(
            "<h2>Compte : {}</h2>".format(obj.provider_clt.name))
        self.obj = obj
        self.table_p = table_p
        self.provid_clt_id = table_p.provid_clt_id
        self.parent = parent
        # self.title.setAlignment(Qt.AlignHCenter)
        title_hbox = QHBoxLayout()
        title_hbox.addWidget(self.title)
        report_hbox = QGridLayout()

        report_hbox.addWidget(FLabel(obj.display_name()), 0, 0)
        # delete and cancel hbox
        button_box = QHBoxLayout()

        # Delete Button widget.
        delete_but = Button(u"Supprimer")
        button_box.addWidget(delete_but)
        delete_but.clicked.connect(self.delete)
        # Cancel Button widget.
        cancel_but = Button(u"Annuler")
        button_box.addWidget(cancel_but)
        cancel_but.clicked.connect(self.cancel)

        # Create the QVBoxLayout contenaire.
        vbox = QVBoxLayout()
        vbox.addLayout(title_hbox)
        vbox.addLayout(report_hbox)
        vbox.addLayout(button_box)
        self.setLayout(vbox)

    def cancel(self):
        self.close()
        return False

    def delete(self):
        self.obj.deletes_data()
        self.cancel()
        self.table_p.refresh_(provid_clt_id=self.provid_clt_id)
        self.parent.Notify("le rapport à été bien supprimé", "error")
