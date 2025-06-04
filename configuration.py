#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu
# maintainer: Fad
from __future__ import absolute_import, division, print_function, unicode_literals

import os
from pathlib import Path

# from static import Constants
from Common.cstatic import CConstants

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
    APP_VERSION = 1
    APP_DATE = "11/2017"
    img_media = os.path.join(os.path.join(ROOT_DIR, "static"), "images/")
    APP_LOGO = os.path.join(img_media, "logo.png")
    APP_LOGO_ICO = os.path.join(img_media, "logo.ico")
    BASE_URL = "http://file-repo.ml"
    BASE_URL = "http://192.168.6.6:8000"

    # Configuration de l'application
    BASE_DIR = Path(__file__).parent.absolute()
    MEDIA_DIR = os.path.join(BASE_DIR, "media")
    IMG_MEDIA = os.path.join(MEDIA_DIR, "img")
    ICON_MEDIA = os.path.join(MEDIA_DIR, "icons")
    
    # Configuration de la base de données
    DB_PATH = os.path.join(BASE_DIR, "database.db")
    
    # Configuration des logs
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    LOG_FILE = os.path.join(LOG_DIR, "app.log")
    
    # Configuration de l'interface
    DEFAULT_FONT = "Sans Serif"
    DEFAULT_FONT_SIZE = 10
    WINDOW_MIN_WIDTH = 800
    WINDOW_MIN_HEIGHT = 600
    
    # Configuration des sauvegardes
    BACKUP_DIR = os.path.join(BASE_DIR, "backups")
    
    # Création des répertoires nécessaires
    @classmethod
    def create_directories(cls):
        """Crée les répertoires nécessaires s'ils n'existent pas"""
        directories = [
            cls.MEDIA_DIR,
            cls.IMG_MEDIA,
            cls.ICON_MEDIA,
            cls.LOG_DIR,
            cls.BACKUP_DIR
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

# Création des répertoires au chargement du module
Config.create_directories()
