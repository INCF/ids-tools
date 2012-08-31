#!/usr/bin/env python

from setuptools import setup
from ids import __version__

setup(name = "ids-tools",
      version = __version__,
      description = "INCF Dataspace tools",
      long_description = open("README.rst").read(),
      author = "Chris Smith",
      author_email = "chris@distributedbio.com",
      scripts = ["bin/ids-copy-dataset", "bin/ids-event-logger",
                 "bin/ids-init", "bin/ids-manage-resource",
                 "bin/ids-search-meta", "bin/ids-setup-data-server",
                 "bin/ids-setup-namespace", "bin/ids-setup-zone",
                 "bin/ids-sync-ldap-users", "bin/ids-sync-peer-zones",
                 "bin/ids-sync-users", "bin/ids-sync-zone-rules"],
      url = "https://github.com/INCF/ids-tools/",
      packages = ["ids", "ids.rules"],
      package_data = {"ids.rules": ["ids-apply-rules.r",
                                    "ids-push-rules.r",
                                    "ids-store-rules.r"]},
      include_package_data = True,
      license = "ASL",
      platforms = "Posix; MacOS X",
      classifiers = ["Development Status :: 3 - Alpha",
                     "Intended Audience :: Science/Research",
                     "Intended Audience :: System Administrators",
                     "License :: OSI Approved :: Apache Software License",
                     "Operating System :: OS Independent",
                     "Topic :: Internet",
                     "Topic :: System :: Archiving",
                     "Topic :: System :: Distributed Computing",
                     "Programming Language :: Python :: 2",
                     "Programming Language :: Python :: 2.7"]
      )
