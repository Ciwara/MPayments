#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Created by: python.exe -m py2exe main_app.py -W setup-win.py

import os
import sys
from distutils.core import setup

import py2exe
from configuration import Config

sys.path.append(os.path.abspath("../"))


class Target(object):
    """Target is the baseclass for all executables that are created.
    It defines properties that are shared by all of them.
    """

    def __init__(self, **kw):
        self.__dict__.update(kw)

        # the VersionInfo resource, uncomment and fill in those items
        # that make sense:

        # The 'version' attribute MUST be defined, otherwise no versioninfo will be built:
        # self.version = "1.0"

        self.company_name = "BaraCorp"
        self.copyright = "Copyright BaraCorp © 2015"
        self.legal_copyright = "Copyright BaraCorp © 2015"
        self.legal_trademark = ""
        self.product_version = Config.APP_VERSION
        self.product_name = Config.APP_NAME

        self.private_build = "foo"
        self.special_build = "bar"

    def copy(self):
        return Target(**self.__dict__)

    def __setitem__(self, name, value):
        self.__dict__[name] = value


RT_BITMAP = 2
RT_MANIFEST = 24

# A manifest which specifies the executionlevel
# and windows common-controls library version 6

manifest_template = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="5.0.0"
    processorArchitecture="*"
    name="%(prog)s"
    type="win32"
  />
  <description>%(prog)s</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel
            level="%(level)s"
            uiAccess="false">
        </requestedExecutionLevel>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="*"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
  </dependency>
</assembly>
"""

main_app = Target(
    # We can extend or override the VersionInfo of the base class:
    # version = "1.0",
    # file_description = "File Description",
    # comments = "Some Comments",
    # internal_name = "spam",
    script=Config.NAME_MAIN,  # path of the main script
    # Allows to specify the basename of the executable, if different from 'main_app'
    # dest_base = "main_app",
    # Icon resources:[(resource_id, path to .ico file), ...]
    # icon_resources=[(1, r"main_app.ico")]
    other_resources=[
        (
            RT_MANIFEST,
            1,
            (manifest_template % dict(prog=Config.NAME_MAIN, level="asInvoker")).encode(
                "utf-8"
            ),
        ),
        # for bitmap resources, the first 14 bytes must be skipped when reading the file:
        #                    (RT_BITMAP, 1, open("bitmap.bmp", "rb").read()[14:]),
    ],
)


py2exe_options = dict(
    # packages=['reportlab'],
    #    ignores = "dotblas gnosis.xml.pickle.parsers._cexpat mx.DateTime".split(),
    # dll_excludes = "MSVCP90.dll mswsock.dll powrprof.dll".split(),
    includes=["sip", "PyQt4"],
    excludes=["tkinter", "toFspecials"],
    optimize=2,
    compressed=True,  # uncompressed may or may not have a faster startup
    bundle_files=3,
    dist_dir="dist",
)


# Some options can be overridden by command line options...

setup(
    name="name",
    # console based executables
    console=[main_app],
    # windows subsystem executables (no console)
    windows=[
        {"script": Config.NAME_MAIN, "icon_resources": [(0, Config.APP_LOGO_ICO)]}
    ],
    # py2exe options
    zipfile=None,
    options={
        "py2exe": py2exe_options,
    },
)
