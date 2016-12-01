
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
    def __init__(self, **kwargs):
        """Initialize the module API."""
        pass

    @property
    @abc.abstractmethod
    def commands(self):
        """Get the module's commands."""
        return {}

    @classmethod
    @abc.abstractmethod
    def get_module_args(cls):
        """Get the names of the module arguments.

        This is a dictionary of {name: required}, where name is the name of
        the argument, and required is True if the argument must be present.

        """
        return {}
    # XXX: It would've been nice to have module_args be a class property,
    # but @property doesn't work on classmethods. We could get around
    # that by defining our own metaclass, as a subclass of abc.ABCMeta, and
    # defining the property there. Since it's a metaclass, the property
    # affects the class, so no need for @classmethod. This is too complex,
    # though, for little gain.

