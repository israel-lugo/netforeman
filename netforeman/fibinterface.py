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


"""Base classes for all FIB interfaces."""



class FIBError(Exception):
    """Error from a FIB interface."""

    def __init__(self, msg, orig=None):
        self.msg = msg
        self.orig=orig

    def __str__(self):
        return self.msg


class FIBInterface:
    """Base class for all the Interface to an underlying FIB.

    This is a base class for specific FIB interfaces. It must be
    subclassed, and its methods overriden for any implemented operation.

    Default methods raise NotImplementedError; leave them at that for
    unsupported operations.

    """

    def __init__(self):
        pass

    def get_routes(self, family):
        """Get routes from the underlying FIB."""
        raise NotImplementedError()

    def add_route(self, r):
        """Add a route to the FIB.

        Raises route.FIBError in case of error (such as no permissions,
        route already exists, and so on).

        """
        raise NotImplementedError()

    def change_route(self, r):
        """Change an existing route in the FIB.

        Raises route.FIBError in case of error (such as no permissions,
        route doesn't exist, and so on).

        """
        raise NotImplementedError()

    def delete_route(self, r):
        """Delete an existing route from the FIB.

        Raises route.FIBError in case of error (such as no permissions,
        route doesn't exist, and so on).

        """
        raise NotImplementedError()

    def replace_route(self, r):
        """Replace a route in the FIB.

        If the route exists, it is changed. If it doesn't exist, a new one
        is created. Raises route.FIBError in case of error (such as no
        permissions, and so on).

        """
        raise NotImplementedError()

