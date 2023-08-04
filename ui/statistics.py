#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad


from datetime import datetime, date

from PyQt4.QtGui import (QVBoxLayout, QGridLayout, QMenu)
from PyQt4.QtCore import Qt, QDate

from configuration import Config
from Common.ui.common import (
    FormLabel, FWidget, FPeriodHolder, FPageTitle, BttExportPDF,
    BttExportXLSX, FormatDate, ExtendedComboBox)
from Common.ui.table import FTableWidget, TotalsWidget
from Common.ui.util import is_float, date_to_datetime, date_on_or_end
from data_helper import device_amount

from models import Payment, ProviderOrClient
from ui.payment_edit_add import EditOrAddPaymentrDialog


class StatisticsViewWidget(FWidget, FPeriodHolder):

    def __init__(self, parent=0, *args, **kwargs):

        super(StatisticsViewWidget, self).__init__(
            parent=parent, *args, **kwargs)
        FPeriodHolder.__init__(self, *args, **kwargs)

        self.parent = parent

        self.title = u"Movements"
        self.compte = self.compte_name = "Tous"

        self.on_date_field = FormatDate(
            QDate(date.today().year, date.today().month, 1))
        self.on_date_field.dateChanged.connect(self.refresh_prov_clt)
        self.end_date_field = FormatDate(QDate.currentDate())
        self.end_date_field.dateChanged.connect(self.refresh_prov_clt)
        self.now = datetime.now().strftime(Config.DATEFORMAT)
        self.balanceField = FormLabel("")
        balance_box = QGridLayout()
        balance_box.addWidget(self.balanceField, 0, 3)
        balance_box.setColumnStretch(0, 1)

        self.string_list = [""] + [
            (clt.name) for clt in ProviderOrClient.select().where(
                ProviderOrClient.type_ == ProviderOrClient.CLT).order_by(
                ProviderOrClient.name.desc())]
        self.title_field = FPageTitle("Tous")
        self.compte_field = ExtendedComboBox()
        self.compte_field.addItems(self.string_list)
        self.compte_field.setToolTip("Nom du compte")
        self.compte_field.currentIndexChanged.connect(
            self.refresh_prov_clt)

        self.btt_pdf_export = BttExportPDF("")
        self.btt_pdf_export.clicked.connect(self.export_pdf)
        self.btt_xlsx_export = BttExportXLSX("")
        self.btt_xlsx_export.clicked.connect(self.export_xlsx)

        if Config.CISS:
            self.table = RapportCISSTableWidget(parent=self)
        else:
            self.table = RapportTableWidget(parent=self)

        editbox = QGridLayout()
        editbox.addWidget(self.compte_field, 1, 0)
        editbox.addWidget(FormLabel(u"Date debut"), 1, 1)
        editbox.addWidget(self.on_date_field, 1, 2)
        editbox.addWidget(FormLabel(u"Date fin"), 1, 3)
        editbox.addWidget(self.end_date_field, 1, 4)
        editbox.setColumnStretch(5, 2)
        editbox.addWidget(self.btt_pdf_export, 1, 6)
        editbox.addWidget(self.btt_xlsx_export, 1, 7)

        vbox = QVBoxLayout()
        vbox.addWidget(self.title_field)
        vbox.addLayout(editbox)
        vbox.addWidget(self.table)
        vbox.addLayout(balance_box)
        self.setLayout(vbox)

    def refresh_prov_clt(self):
        self.compte_name = self.compte_field.lineEdit().text()

        self.title_field.setText(self.compte_name)
        if self.compte_name != "":
            self.compte = ProviderOrClient.get(name=self.compte_name)

        self.table.refresh_()

    def export_pdf(self):
        from Common.exports_pdf import export_dynamic_data
        export_dynamic_data(self.table.dict_data())

    def export_xlsx(self):
        from Common.exports_xlsx import export_dynamic_data
        export_dynamic_data(self.table.dict_data())

    def display_balance(self, amount_text):
        return """ <h2>Solde du {}: <b>{}</b></h2>
               """.format(self.now, amount_text)


class RapportCISSTableWidget(FTableWidget):

    def __init__(self, parent, *args, **kwargs):

        FTableWidget.__init__(self, parent=parent, *args, **kwargs)

        self.hheaders = [
            "Date", "Libelle opération", "Poids (kg)", "Débit", "Crédit", "Solde", ""]
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

        self.parent = parent

        self.sorter = True
        self.stretch_columns = [0, 1, 2, 3, 4, 5]
        self.align_map = {0: 'l', 1: 'l', 2: 'r', 3: 'r', 4: 'r', 5: 'r'}
        # self.ecart = -5
        self.display_vheaders = False
        self.refresh_()

    def refresh_(self):
        """ """

        # self.totals_debit = 0
        # self.totals_credit = 0
        self.balance_tt = 0
        self.on_date = date_to_datetime(self.parent.on_date_field.text())
        self.end_date = date_to_datetime(self.parent.end_date_field.text())

        self._reset()
        self.set_data_for()
        self.refresh()

        self.parent.balanceField.setText(
            self.parent.display_balance(device_amount(self.balance_tt)))

        self.hideColumn(len(self.hheaders) - 1)

    def set_data_for(self):
        qs = Payment.select()
        if not isinstance(self.parent.compte, str):
            qs = qs.where(Payment.provider_clt == self.parent.compte)
        else:
            self.parent.compte = "Tous"
        qs = qs.select().where(
            Payment.status == False, Payment.date <= date_on_or_end(
                self.end_date, on=False), Payment.date >= date_on_or_end(
                self.on_date)).order_by(Payment.date.asc())
        self.data = [(
            pay.date, pay.libelle, pay.weight, pay.debit, pay.credit,
            pay.balance, pay.id) for pay in qs]

    def popup(self, pos):

        # from ui.ligne_edit import EditLigneViewWidget
        from ui.deleteview import DeleteViewWidget
        # from data_helper import check_befor_update_payment

        if (len(self.data) - 1) < self.selectionModel().selection().indexes(
        )[0].row():
            return False
        menu = QMenu()
        editaction = menu.addAction("Modifier cette ligne")
        delaction = menu.addAction("Supprimer cette ligne")
        action = menu.exec_(self.mapToGlobal(pos))
        row = self.selectionModel().selection().indexes()[0].row()
        payment = Payment.get(id=self.data[row][-1])
        if action == editaction:
            self.parent.open_dialog(EditOrAddPaymentrDialog, modal=True,
                                    payment=payment, table_p=self)

        if action == delaction:
            self.parent.open_dialog(DeleteViewWidget, modal=True,
                                    table_p=self, obj=payment)

    def extend_rows(self):

        self.parent.btt_pdf_export.setEnabled(True)
        self.parent.btt_xlsx_export.setEnabled(True)
        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 2)
        self.setSpan(nb_rows + 2, 2, 2, 4)

        self.totals_weight = 0
        self.totals_debit = 0
        self.totals_credit = 0
        cp = 0
        for row_num in range(0, self.data.__len__()):
            mtt_weight = is_float(str(self.item(row_num, 2).text()))
            mtt_debit = is_float(str(self.item(row_num, 3).text()))
            mtt_credit = is_float(str(self.item(row_num, 4).text()))
            # if cp == 0:
            #     last_balance = is_float(str(self.item(row_num, 4).text()))
            self.totals_weight += mtt_weight
            self.totals_debit += mtt_debit
            self.totals_credit += mtt_credit
            cp += 1

        # self.balance_tt = last_balance
        self.balance_tt = self.totals_credit - self.totals_debit

        self.label_mov_tt = u"Totals mouvements: "
        self.setItem(nb_rows, 1, TotalsWidget(self.label_mov_tt))
        self.setItem(nb_rows, 2, TotalsWidget(
            device_amount(self.totals_weight, dvs="Kg", aftergam=3)))
        self.setItem(nb_rows, 3, TotalsWidget(
            device_amount(self.totals_debit)))
        self.setItem(nb_rows, 4, TotalsWidget(
            device_amount(self.totals_credit)))

    def dict_data(self):
        title = "versements"
        return {
            'file_name': "{}-{}".format(title, self.parent.now),
            'headers': self.hheaders[:-1],
            'data': self.data,
            "extend_rows": [(1, self.label_mov_tt),
                            (2, device_amount(self.totals_weight, dvs="Kg", aftergam=3)),
                            (3, self.totals_debit),
                            (4, self.totals_credit), ],
            "footers": [("C", "E", "Solde du {} = {}".format(
                self.end_date.strftime("%x"), device_amount(
                        self.balance_tt)))],
            'sheet': title,
            # 'title': self.title,
            'widths': self.stretch_columns,
            'format_money': ["C:C", "D:D", "E:E", ],
            # 'exclude_row': len(self.data) - 1,
            'others': [("A7", "C7", "Compte : {}".format(
                self.parent.compte_name)), ],
            "date": "Du {} au {}".format(
                self.on_date.strftime("%x"), self.end_date.strftime("%x"))
        }


class RapportTableWidget(FTableWidget):

    def __init__(self, parent, *args, **kwargs):

        FTableWidget.__init__(self, parent=parent, *args, **kwargs)

        self.hheaders = [
            "Date", "Libelle opération", "Débit", "Crédit", "Solde", ""]
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.popup)

        self.parent = parent

        # self.sorter = True
        self.stretch_columns = [0, 1, 2, 3, 4]
        self.align_map = {0: 'l', 1: 'l', 2: 'r', 3: 'r', 4: 'r'}
        self.display_vheaders = False
        if not Config.DEVISE_PEP_PROV:
            self.refresh_()

    def refresh_(self):
        """ """

        # self.totals_debit = 0
        # self.totals_credit = 0
        self.balance_tt = 0
        self.on_date = date_to_datetime(self.parent.on_date_field.text())
        self.end_date = date_to_datetime(self.parent.end_date_field.text())

        self._reset()
        self.set_data_for()
        self.refresh()
        self.refresh()

        self.parent.balanceField.setText(
            self.parent.display_balance(device_amount(self.balance_tt)))

        self.hideColumn(len(self.hheaders) - 1)

    def set_data_for(self):
        qs = Payment.select()
        if not isinstance(self.parent.compte, str):
            qs = qs.where(Payment.provider_clt == self.parent.compte)
        else:
            self.parent.compte = "Tous"
        qs = qs.select().where(
            Payment.status == False, Payment.date <= date_on_or_end(
                self.end_date, on=False), Payment.date >= date_on_or_end(
                self.on_date)).order_by(Payment.date.asc())
        self.data = [(
            pay.date, pay.libelle, pay.debit, pay.credit,
            pay.balance, pay.id) for pay in qs]

    def popup(self, pos):

        # from ui.ligne_edit import EditLigneViewWidget
        from ui.deleteview import DeleteViewWidget
        # from data_helper import check_befor_update_payment

        if (len(self.data) - 1) < self.selectionModel().selection().indexes(
        )[0].row():
            return False
        menu = QMenu()
        editaction = menu.addAction("Modifier cette ligne")
        delaction = menu.addAction("Supprimer cette ligne")
        action = menu.exec_(self.mapToGlobal(pos))
        row = self.selectionModel().selection().indexes()[0].row()
        payment = Payment.get(id=self.data[row][-1])
        if action == editaction:
            self.parent.open_dialog(EditOrAddPaymentrDialog, modal=True,
                                    payment=payment, table_p=self)

        if action == delaction:
            self.parent.open_dialog(DeleteViewWidget, modal=True,
                                    table_p=self, obj=payment)

    def extend_rows(self):
        self.parent.btt_pdf_export.setEnabled(True)
        self.parent.btt_xlsx_export.setEnabled(True)
        nb_rows = self.rowCount()
        self.setRowCount(nb_rows + 1)
        self.setSpan(nb_rows + 2, 2, 2, 4)

        self.totals_debit = 0
        self.totals_credit = 0
        cp = 0
        for row_num in range(0, self.data.__len__()):
            mtt_debit = is_float(str(self.item(row_num, 2).text()))
            mtt_credit = is_float(str(self.item(row_num, 3).text()))

            self.totals_debit += mtt_debit
            self.totals_credit += mtt_credit
            cp += 1

        # self.balance_tt = last_balance
        self.balance_tt = self.totals_credit - self.totals_debit

        self.label_mov_tt = u"Totals mouvements: "
        self.setItem(nb_rows, 1, TotalsWidget(self.label_mov_tt))
        self.setItem(nb_rows, 2, TotalsWidget(
            device_amount(self.totals_debit)))
        self.setItem(nb_rows, 3, TotalsWidget(
            device_amount(self.totals_credit)))

    def dict_data(self):
        title = "versements"
        return {
            'file_name': "{}-{}".format(title, self.parent.now),
            'headers': self.hheaders[:-1],
            'data': self.data,
            "extend_rows": [(1, self.label_mov_tt),
                            (2, self.totals_debit),
                            (3, self.totals_credit), ],
            "footers": [("C", "E", "Solde du {} = {}".format(
                self.end_date.strftime("%x"), device_amount(
                        self.balance_tt))), ],
            'sheet': title,
            # 'title': self.title,
            'widths': self.stretch_columns,
            'format_money': ["C:C", "D:D", "E:E", ],
            # 'exclude_row': len(self.data) - 1,
            'others': [("A7", "C7", "Compte : {}".format(
                self.parent.compte_name)), ],
            "date": "Du {} au {}".format(
                self.on_date.strftime("%x"), self.end_date.strftime("%x"))
        }
