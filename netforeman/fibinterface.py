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


"""Base classes for all FIB interfaces."""


import netaddr

import netforeman.moduleapi


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

    def get_route_to(self, rm):
        """Get a route from the FIB matching the specified route.

        Raises fibinterface.FIBError in case of error (such as no
        permissions, route doesn't exist, and so on).

        """
        raise NotImplementedError()

    def replace_route(self, r):
        """Replace a route in the FIB.

        If the route exists, it is changed. If it doesn't exist, a new one
        is created. Raises route.FIBError in case of error (such as no
        permissions, and so on).

        """
        raise NotImplementedError()


class FIBModuleAPI(netforeman.moduleapi.ModuleAPI):
    """FIB module API."""

    def __init__(self, conf):
        """Initialize the FIB module.

        Receives a pyhocon.config_tree.ConfigTree object, containing the
        module's config tree.

        """
        # TODO: Implement _create_fib(). Depends on which FIB we are.
        # Probably best done at the subclass level (abstractmethod). That
        # means this should be an abstract class.
        self.fib = self._create_fib()

        self.conf = conf

    def run(self):
        """Run any configured verifications and actions in this module."""

        for subconf in self.conf.get_list('route_checks', default=[]):
            self.route_check(subconf)

    def route_check(self, conf):
        """Do route check.

        Receives a pyhocon.config_tree.ConfigTree objects, containing the
        description of the route check to perform.

        """
        dest = netaddr.IPNetwork(self._get_conf(conf, 'dest'))
        non_null = conf.get_bool('non_null', default=False)
        nexthops_any = conf.get_list('nexthops_any', default=[])
        on_error = self._get_conf(conf, 'on_error')

        # TODO: Finish this. Use fib.get_route_to, and see if it the
        # route's nexthop is contained in nexthops_any (if there is a
        # nexthops_any). On error, run the stuff in on_error.

    @property
    def actions(self):
        """Get the routing table module's actions."""
        return {'add_route': self.add_route}

    def _load_fib_module(self, name):
        """Load a FIB module."""
        return importlib.import_module("{:s}.{:s}".format(__package__, name))



API = FIBModuleAPI

