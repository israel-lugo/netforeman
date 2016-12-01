#! /usr/bin/env python3

# NetForeman - making sure your network is running smoothly
# Copyright (C) 2016 Israel G. Lugo
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

        # load the modules
        self.modules = [
                importlib.import_module("{:s}.{:s}".format(__package__, module))
            for module in modules_to_load
        ]

        # create the API object for every loaded module
        self.module_apis = [
            m.API(**self.get_module_args(m))
            for m in self.modules
        ]


    def get_module_args(self, module):
        """Get the configured arguments for a certain module.

        Returns a config tree of arguments. Raises ParseError if any
        required arguments are missing.

        """
        args = module.API.get_module_args()

        # if the module has no arguments, there's nothing to check
        if not args:
            return {}

        # use the module's relative name
        module_name = module.__name__.split('.')[-1]

        if module_name not in self.conf:
            raise ParseError("missing required section '{:s}'".format(module_name))

        module_conf = self.conf.get_config(module_name)

        # make sure everything's there
        for name, required in args.items():
            if required and name not in module_conf:
                raise ParseError("missing required argument '{:s}.{:s}'".format(module_name, name))

        return module_conf


