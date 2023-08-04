#!/usr/bin/env python
# -*- encoding: utf-8
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad
from __future__ import absolute_import, division, print_function, unicode_literals

from Common.ui.util import formatted_number


def check_befor_update_payment(pay):
    from models import Payment

    balance = pay.balance
    lt = []
    for rpt in pay.next_rpts():
        previous_balance = int(rpt.last_balance_payment())
        if rpt.type_ == Payment.CREDIT:
            balance = previous_balance + int(rpt.credit)
            lt.append("{} = last {} + {}".format(balance, previous_balance, rpt.credit))
        if rpt.type_ == Payment.DEBIT:
            balance = previous_balance - int(rpt.debit)
            lt.append("{} = last {} - {}".format(balance, previous_balance, rpt.debit))
        # if balance < 0:
        #     return False
    return True


def device_amount(value, provider=None, dvs=None, aftergam=2):
    from Common.models import Organization
    from configuration import Config
    from models import ProviderOrClient

    if dvs:
        return "{} {}".format(formatted_number(value, aftergam=aftergam), dvs)

    organ = Organization().get(id=1)

    if not Config.DEVISE_PEP_PROV or not provider:
        dvs = organ.DEVISE.get(organ.devise)
    else:
        if isinstance(provider, str):
            dvs = organ.DEVISE.get(organ.devise)
        elif isinstance(provider, int):
            provider = ProviderOrClient().get(id=int(provider))
            dvs = provider.DEVISE.get(provider.devise)
        else:
            provider = provider
            dvs = provider.DEVISE.get(provider.devise)

    v = formatted_number(value, aftergam=aftergam)
    if dvs == "$":
        return "{d}{v}".format(v=v, d=dvs)
    else:
        return "{v}{d}".format(v=v, d=dvs)
