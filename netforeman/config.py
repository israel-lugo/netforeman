#! /usr/bin/env python3

# NetForeman - making sure your network is running smoothly
# Copyright (C) 2016, 2017 Israel G. Lugo
#
# This file is part of NetForeman.
#
# NetForeman is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# NetForeman is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with NetForeman. If not, see <http://www.gnu.org/licenses/>.
#
# For suggestions, feedback or bug reports: israel.lugo@lugosys.com


"""Configuration parser."""

import importlib

import pyhocon


class ParseError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class ModuleInfo:
    """Information about a loaded module."""

    def __init__(self, name, module, api):
        self.name = name
        self.module = module
        self.api = api


class Configurator:

    def __init__(self, filename):
        """Initializes a Configurator by parsing a configuration file.

        Raises ParseError in case of error.

        """
        self.filename = filename

        try:
            self.conf = pyhocon.ConfigFactory.parse_file(filename)
        except pyhocon.exceptions.ConfigException as e:
            raise ParseError(str(e))

    def load_modules(self):
        """Load configured modules."""
        try:
            modules_to_load = self.conf['modules']
        except pyhocon.exceptions.ConfigMissingException as e:
            raise ParseError("missing mandatory section 'modules'")

        self.loaded_modules = []
        self.modules_by_name = {}
        for name in modules_to_load:
            if name in self.modules_by_name:
                raise ParseError("module '{:s}' duplicated, already loaded".format(name))

            module = importlib.import_module("{:s}.{:s}".format(__package__, name))
            api = module.API(self.get_module_conf(module))
            modinfo = ModuleInfo(name, module, api)

            self.loaded_modules.append(modinfo)
            self.modules_by_name[name] = modinfo

    def get_module_conf(self, module):
        """Get the a module's config tree.

        Returns a config tree of arguments. Raises ParseError if the tree
        is missing.

        """
        # use the module's relative name
        module_name = module.__name__.split('.')[-1]

        if module_name not in self.conf:
            raise ParseError("missing required section '{:s}'".format(module_name))

        module_conf = self.conf.get_config(module_name)

        return module_conf

