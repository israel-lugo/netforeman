
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


"""API definition for all NetForeman modules."""


import abc


class ModuleAPI(metaclass=abc.ABCMeta):
    """Base class for the API of all NetForeman modules."""

    @abc.abstractmethod
    def __init__(self, conf):
        """Initialize the module API.

        Receives a pyhocon.config_tree.ConfigTree object, containing the
        module's config tree.

        """
        pass

    @property
    @abc.abstractmethod
    def commands(self):
        """Get the module's commands."""
        return {}

    @staticmethod
    def _get_conf(conf, name, required=True):
        """Get a value from a pyhocon.config_tree.ConfigTree.

        If the value is missing and required is True, raises a KeyError
        exception. If the value is missing and required is False, returns
        None.

        """
        value = conf.get(name, None)
        if value is None and required:
            raise KeyError("missing required argument '{:s}'".format(name))

        return value
