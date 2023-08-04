#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad
from __future__ import absolute_import, division, print_function, unicode_literals

from Common.cdatabase import AdminDatabase
from models import Payment, ProviderOrClient
from playhouse.migrate import (
    BooleanField,
    CharField,
    FloatField,
    ForeignKeyField,
    IntegerField,
)


class Setup(AdminDatabase):

    """docstring for FixtInit"""

    def __init__(self):
        super(AdminDatabase, self).__init__()

        self.LIST_CREAT.append(Payment)
        self.LIST_CREAT.append(ProviderOrClient)

        self.LIST_MIGRATE += [
            ("Organization", "logo_org", CharField(null=True)),
            ("Organization", "after_cam", IntegerField(default=0)),
            ("ProviderOrClient", "deleted", BooleanField(default=False)),
            ("ProviderOrClient", "devise", CharField(default="xof")),
            ("ProviderOrClient", "phone", IntegerField(null=True)),
            ("Payment", "weight", FloatField(null=True)),
            ("Payment", "name", CharField(null=True)),
            ("Transfert", "name", CharField(null=True)),
        ]
        self.make_migrate(db_v=3)
