#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad

from PyQt4.QtGui import (
    QVBoxLayout, QDialog, QTextEdit, QFormLayout, QComboBox)

from Common.ui.util import check_is_empty, field_error
from Common.ui.common import (
    FWidget, Button, FormLabel, LineEdit, IntLineEdit)
import peewee
from models import CooperativeMember

from configuration import Config


class EditOrAddMemberDialog(QDialog, FWidget):

    def __init__(self, table_p, parent, coop_member=None, *args, **kwargs):
        FWidget.__init__(self, parent, *args, **kwargs)

        self.table_p = table_p
        self.coop_member = coop_member
        self.parent = parent
        if self.coop_member:
            self.new = False
            self.title = u"Modification de {} {}".format(self.coop_member.type_,
                                                         self.coop_member.name)
            self.succes_msg = u"{} a été bien mise à jour".format(
                self.coop_member.type_)
        else:
            self.new = True
            self.succes_msg = u"Client a été bien enregistré"
            self.title = u"Création d'un nouvel client"
            self.coop_member = CooperativeMember()
        self.setWindowTitle(self.title)

        vbox = QVBoxLayout()
        # vbox.addWidget(FPageTitle(u"Utilisateur: %s " % self.coop_member.name))
        self.liste_devise = []
        # Combobox widget
        self.box_devise = QComboBox()
        for index, value in enumerate(self.liste_devise):
            self.box_devise.addItem(
                "{} {}".format(self.liste_devise[value], value))
            if self.coop_member.devise == value:
                self.box_devise.setCurrentIndex(index)

        if self.coop_member.phone:
            phone = str(self.coop_member.phone)
        else:
            phone = ""
        self.nameField = LineEdit(self.coop_member.name)
        self.phone_field = IntLineEdit(phone)
        # self.phone_field.setInputMask("D9.99.99.99")
        self.legal_infos = LineEdit(self.coop_member.legal_infos)
        self.address = QTextEdit(self.coop_member.address)
        self.email = LineEdit(self.coop_member.email)

        formbox = QFormLayout()
        formbox.addRow(FormLabel(u"Nom complete : *"), self.nameField)

        if not self.new:
            formbox.addRow(FormLabel(u"Tel: *"), self.phone_field)
            formbox.addRow(FormLabel(u"E-mail :"), self.email)
            formbox.addRow(FormLabel(u"addresse complete :"), self.address)
            formbox.addRow(FormLabel(u"Info. legale :"), self.legal_infos)

        butt = Button(u"Enregistrer")
        butt.clicked.connect(self.save_edit)
        formbox.addRow("", butt)

        vbox.addLayout(formbox)
        self.setLayout(vbox)

    def save_edit(self):
        ''' add operation '''
        # print("Save")
        phone = self.phone_field.text()
        # field_error
        if check_is_empty(self.nameField):
            return

        coop_member = self.coop_member
        coop_member.name = str(self.nameField.text())

        if Config.DEVISE_PEP_PROV:
            coop_member.devise = str(self.box_devise.currentText().split()[1])

        if not self.new:
            if phone != "":
                coop_member.phone = int(phone)
            coop_member.email = str(self.email.text())
            coop_member.legal_infos = str(self.legal_infos.text())
            coop_member.address = str(self.address.toPlainText())

        try:
            coop_member.save()
            self.close()
            self.table_p.refresh_()
            self.parent.Notify(u"Le Compte %s a été mise à jour" %
                               coop_member.name, "success")
        except peewee.IntegrityError as e:
            # print("IntegrityError ", e)
            field_error(
                self.nameField, "Ce nom existe dans la basse de donnée.")
