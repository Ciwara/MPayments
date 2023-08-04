#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fadiga

from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

from Common.models import BaseModel, FileJoin, Owner
from data_helper import device_amount
from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    TextField,
)

FDATE = "%c"
NOW = datetime.now()


class ProviderOrClient(BaseModel):

    """Represents the company emmiting the invoices"""

    # class Meta:
    #     order_by = ('name',)

    CLT = "Client"
    FSEUR = "Fournisseur"
    TYPES = [CLT, FSEUR]

    USA = "dollar"
    XOF = "xof"
    EURO = "euro"
    DEVISE = {USA: "$", XOF: "F", EURO: "€"}

    name = CharField(unique=True, verbose_name=("Nom de votre entreprise"))
    address = TextField(null=True, verbose_name=("Adresse principale de votre société"))
    phone = IntegerField(
        null=True, verbose_name=("Numero de téléphone de votre entreprise")
    )
    email = CharField(
        null=True, verbose_name=("Adresse électronique de votre entreprise")
    )
    legal_infos = TextField(null=True, verbose_name=("Informations légales"))
    type_ = CharField(max_length=30, choices=TYPES, default=CLT)
    picture = ForeignKeyField(
        FileJoin,
        null=True,
        related_name="file_joins_pictures",
        verbose_name=("image de la societe"),
    )
    devise = CharField(choices=DEVISE, default=XOF)
    deleted = BooleanField(default=False)

    def payments(self):
        return Payment.select().where(Payment.provider_clt == self)

    def delete_data(self):
        self.deleted = True
        self.save()

    def restore_data(self):
        self.deleted = False
        self.save()

    def delete_permanate(self):
        self.delete_instance()

    def is_indebted(self):
        flag = False
        if self.last_remaining() > 0:
            flag = True
        return flag

    def display_name(self):
        return self.__str__()

    def last_payment(self):
        try:
            return (
                Payment.select()
                .where(Payment.provider_client == self)
                .order_by(Payment.date.desc())
                .get()
            )
        except:
            return None

    def last_remaining(self):
        last_r = self.last_payment()
        return last_r.remaining if last_r else 0

    def __str__(self):
        return "{}, {}".format(self.name, self.phone)

    def __unicode__(self):
        return self.__str__()

    @classmethod
    def get_or_create(cls, name, phone, typ):
        try:
            ctct = cls.get(name=name, phone=phone, type_=typ)
        except cls.DoesNotExist:
            ctct = cls.create(name=name, phone=phone, type_=typ)
        return ctct


class Payment(BaseModel):

    """docstring for Payment"""

    class Meta:
        order_by = ("date",)

    DEBIT = "Debit"
    CREDIT = "Credit"

    DC = [DEBIT, CREDIT]

    owner = ForeignKeyField(Owner, verbose_name=("Utilisateur"))
    provider_clt = ForeignKeyField(ProviderOrClient)
    date = DateTimeField(verbose_name=("Date"))
    debit = FloatField(verbose_name=("Débit"))
    credit = FloatField(verbose_name=("Crédit"))
    libelle = CharField(verbose_name=("Libelle"), null=True)
    balance = FloatField(verbose_name=("Solde"))
    weight = FloatField(verbose_name=("Poids"), null=True, default=0)
    type_ = CharField(choices=DC)
    deleted = BooleanField(default=False)
    status = BooleanField(default=False)

    def amount(self):
        return self.credit if self.type_ == self.CREDIT else self.debit

    def __unicode__(self):
        return "Le {date} {type_} d'un montant de {amount}".format(
            date=self.date.strftime(FDATE),
            type_=self.type_,
            amount=self.amount(),
            lib=self.libelle,
        )

    def __str__(self):
        return self.__unicode__()

    def display_name(self):
        return "{amount} {action} le {date}.".format(
            amount=device_amount(self.amount(), self.provider_clt),
            action=self.action(),
            date=self.date.strftime("%x"),
        )

    def action(self):
        return "Créditer" if self.type_ == self.CREDIT else "Débiter"

    def save(self):
        """
        Calcul du balance en stock après une operation."""
        self.owner = Owner.get(Owner.islog == True)
        previous_balance = float(
            self.last_balance_payment().balance if self.last_balance_payment() else 0
        )
        if self.type_ == self.CREDIT:
            self.balance = previous_balance + float(self.credit)
            self.debit = 0
        if self.type_ == self.DEBIT:
            self.balance = previous_balance - float(self.debit)
            self.credit = 0

        super(Payment, self).save()

        if self.next_rpt():
            self.next_rpt().save()

    def next_rpt(self):
        try:
            return self.next_rpts().get()
        except Exception as e:
            print("next_rpt ", e)
            return None

    def next_rpts(self):
        try:
            return (
                Payment.select()
                .where(
                    Payment.provider_clt == self.provider_clt,
                    Payment.date > self.date,
                    Payment.deleted == False,
                )
                .order_by(Payment.date.asc())
            )
        except Exception as e:
            return None
            print("next_rpts ", e)

    def deletes_data(self):
        last = self.last_balance_payment()
        next_ = self.next_rpt()
        self.delete_instance()
        if last:
            last.save()
        else:
            if next_:
                next_.save()
        return

    def last_balance_payment(self):
        try:
            return (
                Payment.select()
                .where(
                    Payment.provider_clt == self.provider_clt,
                    Payment.deleted == False,
                    Payment.date < self.date,
                )
                .order_by(Payment.date.desc())
                .get()
            )
        except Exception as e:
            # print("last_balance_payment", e)
            return None
