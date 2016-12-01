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


def parse(filename):
    """Parse a configuration file.

    Raises ParseError in case of error.

    """
    try:
        conf = pyhocon.ConfigFactory.parse_file(filename)
    except pyhocon.exceptions.ConfigException as e:
        raise ParseError(str(e))

    return conf


def load_modules(conf):
    """Load configured modules."""

    try:
        modules_to_load = conf['modules']
    except pyhocon.exceptions.ConfigMissingException as e:
        raise ParseError("missing mandatory section 'modules'")

    modules = [
            importlib.import_module("{:s}.{:s}".format(__package__, module))
        for module in modules_to_load
    ]

    return modules


# TODO: Create some glue for all this.
#   1. Parse configuration file
#   2. Load modules
#   3. Load arguments for the modules, from dictionaries in the conf
#   4. For each loaded module m, create m.API(m_args)
#   5. ???

