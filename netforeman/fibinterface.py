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


import logging
import netaddr

from netforeman import moduleapi
from netforeman import route
from netforeman import config


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

    def get_default_routes(self, family):
        """Get the list of default routes for the specified family.

        The list will be empty if no default routes exist. Raises
        fibinterface.FIBError in case of error (such as no permissions, and
        so on).

        """
        raise NotImplementedError()

    def replace_route(self, r):
        """Replace a route in the FIB.

        If the route exists, it is changed. If it doesn't exist, a new one
        is created. Raises route.FIBError in case of error (such as no
        permissions, and so on).

        """
        raise NotImplementedError()


class FIBModuleAPI(moduleapi.ModuleAPI):
    """FIB module API."""

    default_metric = 1024
    proto = 'static'

    def __init__(self, conf):
        """Initialize the FIB module.

        Receives a pyhocon.config_tree.ConfigTree object, containing the
        module's config tree.

        """
        super().__init__(conf)

        # TODO: Implement _create_fib(). Depends on which FIB we are.
        # Probably best done at the subclass level (abstractmethod). That
        # means this should be an abstract class.
        self.fib = self._create_fib()

        self.conf = conf

    def run(self, dispatch):
        """Run any configured verifications and actions in this module."""

        for subconf in self.conf.get_list('route_checks', default=[]):
            self.route_check(subconf, dispatch)

    def _route_check_failed(self, dispatch, dest, on_error, error_reason):
        """Handle a failed route check.

        Logs a warning and executes the actions in on_error, which should
        be a list of pyhocon.config_tree.ConfigTree.

        """
        self.logger.warn("route_check to %s failed: %s", dest, error_reason)

        context = moduleapi.ActionContext(self.name,
                "route_check: route to {:s} {:s}".format(str(dest), error_reason))

        for action in on_error:
            try:
                dispatch.execute_action(action, context)
            except config.ParseError as e:
                self.logger.error("unable to execute action: %s", str(e))

    def route_check(self, conf, dispatch):
        """Do route check.

        Receives a pyhocon.config_tree.ConfigTree objects, containing the
        description of the route check to perform.

        """
        dest = netaddr.IPNetwork(self._get_conf(conf, 'dest'))
        self.logger.debug("checking route to %s", dest)

        non_null = conf.get_bool('non_null', default=False)
        nexthops_any = conf.get_list('nexthops_any', default=[])
        on_error = self._get_conf(conf, 'on_error')

        nexthops_any = [netaddr.IPAddress(nh) for nh in nexthops_any]

        rm = route.RouteMatch(dest=dest)

        r = self.fib.get_route_to(rm)

        if r is None:
            self._route_check_failed(dispatch, dest, on_error, "not found")
            return False

        self.logger.debug("route found, via %s", self._nexthops_str(r.nexthops))

        if nexthops_any:
            for nh in r.nexthops:
                if nh.gw in nexthops_any:
                    self.logger.debug("route to %s via expected NH %s", dest, nh.gw)
                    break
            else:
                error_reason = "via {:s}, not in [{:s}]".format(
                        self._nexthops_str(r.nexthops),
                        ', '.join(str(ip) for ip in nexthops_any))
                self._route_check_failed(dispatch, dest, on_error, error_reason)
                return False

        if non_null:
            if r.is_null:
                self._route_check_failed(dispatch, dest, on_error,
                        "{:s}, should be non-null".format(r.rt_type.name))
            else:
                self.logger.debug("route to %s is non-null, as expected", str(dest))

        self.logger.info("route_check to %s check satisfied", dest)

        return True

    @property
    def actions(self):
        """Get the routing table module's actions."""
        return {'add_route': self.add_route}

    def add_route(self, conf, context):
        """Add a route to the FIB.

        Receives a pyhocon.config_tree.ConfigTree instance and an
        ActionContext.

        """
        dest = netaddr.IPNetwork(self._get_conf(conf, 'dest'))
        nexthops = [
                route.NextHop(netaddr.IPAddress(gw), None, route.NHType.via)
                for gw in conf.get_list('nexthops')
        ]
        r = route.Route(dest, dest.prefixlen, nexthops,
                str(self.default_metric), self.proto, route.RouteType.unicast)

        self.logger.info("adding route to %s via %s", dest, self._nexthops_str(r.nexthops))
        self.fib.add_route(r)

    @staticmethod
    def _nexthops_str(nexthops):
        """Return a string representation of a list of nexthops."""
        if len(nexthops) == 1:
            return str(nexthops[0].gw)
        else:
            return "[{:s}]".format(', '.join(str(nh.gw) for nh in nexthops))



API = FIBModuleAPI

# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
