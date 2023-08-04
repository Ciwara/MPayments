#!/usr/bin/env python
# -*- coding: utf-8 -*-
# maintainer: Fad
from __future__ import (
    unicode_literals, absolute_import, division, print_function)

# import os

from PyQt4.QtCore import QDate
from PyQt4.QtGui import (QVBoxLayout, QDialog, QTextEdit, QFormLayout)

from configuration import Config

from Common.ui.util import check_is_empty, date_to_datetime
from Common.ui.common import (FWidget, ButtonSave, FormLabel,
                              FloatLineEdit, FormatDate)

from models import Payment


try:
    unicode
except:
    unicode = str


class EditOrAddPaymentrDialog(QDialog, FWidget):

    def __init__(self, table_p, parent, type_=None, payment=None, *args, **kwargs):
        QDialog.__init__(self, parent, *args, **kwargs)

        self.type_ = type_
        self.payment = payment
        self.parent = parent
        self.table_p = table_p

        weight = ""
        if self.payment:
            self.new = False
            self.type_ = payment.type_
            self.payment_date_field = FormatDate(self.payment.date)
            self.payment_date_field.setEnabled(False)
            self.title = u"Modification de {} {}".format(
                self.payment.type_, self.payment.libelle)
            self.succes_msg = u"{} a été bien mise à jour".format(
                self.payment.type_)

            if self.type_ == Payment.CREDIT:
                amount = payment.credit
            elif self.type_ == Payment.DEBIT:
                amount = payment.debit
                weight = self.payment.weight
        else:
            self.new = True
            self.payment = Payment()
            amount = ""
            self.payment_date_field = FormatDate(QDate.currentDate())
            self.succes_msg = u"Client a été bien enregistré"
            self.title = u"Création d'un nouvel client"

        self.setWindowTitle(self.title)

        self.payment_weight_field = FloatLineEdit(
            unicode(weight).replace(".", ","))
        self.amount_field = FloatLineEdit(unicode(amount).replace(".", ","))
        self.libelle_field = QTextEdit(self.payment.libelle)

        vbox = QVBoxLayout()

        formbox = QFormLayout()
        formbox.addRow(FormLabel(u"Date : *"), self.payment_date_field)
        formbox.addRow(FormLabel(u"Montant : *"), self.amount_field)
        if self.type_ == Payment.DEBIT and Config.CISS:
            formbox.addRow(FormLabel(u"Poids (Kg) : *"),
                           self.payment_weight_field)
        formbox.addRow(FormLabel(u"Libelle :"), self.libelle_field)

        butt = ButtonSave(u"Enregistrer")
        butt.clicked.connect(self.save_edit)
        formbox.addRow("", butt)

        vbox.addLayout(formbox)
        self.setLayout(vbox)

    def save_edit(self):
        ''' add operation '''
        # print("saving")
        if check_is_empty(self.amount_field):
            return
        self.pro_clt_id = self.table_p.provid_clt_id
        payment_date = unicode(self.payment_date_field.text())
        libelle = unicode(self.libelle_field.toPlainText())
        amount = float(unicode(self.amount_field.text(
        ).replace(",", ".").replace(" ", "").replace('\xa0', '')))

        payment = self.payment
        payment.type_ = self.type_
        payment.libelle = libelle
        if self.new:
            payment.date = date_to_datetime(payment_date)
            payment.provider_clt = self.table_p.provider_clt
        if self.type_ == Payment.CREDIT:
            payment.credit = amount
        elif self.type_ == Payment.DEBIT:
            payment.debit = amount

            if Config.CISS:
                if check_is_empty(self.payment_weight_field):
                    return
                payment.weight = float(unicode(self.payment_weight_field.text(
                ).replace(",", ".").replace(" ", "").replace('\xa0', ''))) or 0
        try:
            payment.save()
            self.close()
            self.parent.Notify(
                u"le {type} {lib} à été enregistré avec succès".format(
                    type=self.type_, lib=libelle), "success")
            self.table_p.refresh_(provid_clt_id=self.pro_clt_id)
        except Exception as e:
            print("SAVE Payment : ", e)
            self.parent.Notify(e, "error")
