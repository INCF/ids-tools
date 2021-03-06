#!/usr/bin/env python

from setuptools import setup

from version import get_git_version

setup(name = "incf.ids-tools",
      version = get_git_version(),
      description = "INCF Dataspace tools",
      long_description = open("README.rst").read(),
      author = "Chris Smith",
      author_email = "chris@distributedbio.com",
      maintainer = "Roman Valls Guimera",
      maintainer_email = "roman@incf.org",
      scripts = [
            "bin/ids-copy-dataset",
            "bin/ids-event-logger",
            "bin/ids-init",
            "bin/ids-federate-zone",
            "bin/ids-manage-resource",
            "bin/ids-search-meta",
            "bin/ids-setup-data-server",
            "bin/ids-setup-namespace",
            "bin/ids-setup-zone",
            "bin/ids-sync-ldap-users",
            "bin/ids-sync-peer-zones",
            "bin/ids-sync-users",
            "bin/ids-sync-zone-rules"
            "bin/ids-zone-api"
            ],
      url = "https://github.com/INCF/ids-tools/",
      packages = [
            "ids",
            "ids.api_1_0",
            "ids.rules",
            "ids.fabfile",
            "ids.fabfile.templates"
            ],
      package_data = {
            "ids.rules": ["*.r",],
            "ids.fabfile.templates": ["*.tmpl",]
            },
      include_package_data = True,
      install_requires = [
            "argparse",
            "Fabric",
            "requests"
            ],
      license = "ASL",
      platforms = "Posix; MacOS X",
      classifiers = [
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Science/Research",
            "Intended Audience :: System Administrators",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: OS Independent",
            "Topic :: Internet",
            "Topic :: System :: Archiving",
            "Topic :: System :: Distributed Computing",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 2.7",
            ]
      )
