# from static import Constants

# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad
from __future__ import absolute_import, division, print_function, unicode_literals

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import os

from Common.cstatic import CConstants
from models import Payment

ROOT_DIR = os.path.dirname(os.path.abspath("__file__"))


class Config(CConstants):

    """docstring for Config"""

    DATEFORMAT = "%d-%m-%Y"

    def __init__(self):
        CConstants.__init__(self)

    # ------------------------- Organisation --------------------------#

    DEBUG = False
    # Cise app
    # CISS = True
    CISS = False
    SERV = True
    LSE = True
    # DEVISE_PEP_PROV = True
    DEVISE_PEP_PROV = False

    # des_image_record = "static/img_prod"
    ARMOIRE = "img_prod"
    des_image_record = os.path.join(ROOT_DIR, ARMOIRE)
    PEEWEE_V = 224
    credit = 17
    tolerance = 50
    nb_warning = 5
    ORG_LOGO = None

    # -------- Application -----------#

    NAME_MAIN = "main.py"

    pdf_source = "pdf_source.pdf"
    APP_NAME = "MPayments"
    APP_VERSION = 2
    APP_DATE = "11/2017"
    img_media = os.path.join(os.path.join(ROOT_DIR, "static"), "images/")
    APP_LOGO = os.path.join(img_media, "logo.png")
    APP_LOGO_ICO = os.path.join(img_media, "logo.ico")
    BASE_URL = "http://file-repo.ml"
    BASE_URL = "http://192.168.1.2:8000"
    list_models = [Payment]
