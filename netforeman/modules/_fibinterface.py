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


import abc
import netaddr

from netforeman import moduleapi
from netforeman import route
from netforeman import config



def _nexthops_str(nexthops):
    """Return a string representation of a list of route.NextHop."""
    if len(nexthops) == 1:
        return str(nexthops[0].gw)
    else:
        return "[{:s}]".format(', '.join(str(nh.gw) for nh in nexthops))


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


class ActionAddReplaceRouteSettings(moduleapi.ActionSettings):
    """Settings for ActionAddRoute and ActionReplaceRoute."""

    def __init__(self, action_name, dest, nexthops, metric=1024,
            proto='static', rt_type=route.RouteType.unicast):
        """Initialize an ActionAddReplaceRouteSettings instance.

        dest should be a netaddr.IPNetwork. nexthops should be a list of
        route.NextHop.

        """
        # we're not checking the module name, since we may be used from
        # multiple different types of FIB
        if not (action_name.endswith(".add_route")
                or action_name.endswith(".replace_route")):
            # should never happen if our caller uses Dispatch resolution
            raise config.ParseError("action name '{!s}', should be add_route or replace_route".format(action_name))

        super().__init__(action_name)

        if not nexthops:
            raise config.ParseError("nexthops list must be non-empty")

        self.route = route.Route(dest, dest.prefixlen, nexthops, str(metric),
                                 proto, rt_type)

    @classmethod
    def from_pyhocon(cls, conf, configurator):
        """Create ActionAddReplaceRouteSettings from a pyhocon ConfigTree.

        Returns a newly created instance of ActionAddReplaceRouteSettings. Raises
        config.ParseError in case of error.

        """
        action_name = cls._get_conf(conf, 'action')
        dest = netaddr.IPNetwork(cls._get_conf(conf, 'dest'))
        nexthops = [
                route.NextHop(netaddr.IPAddress(gw), None, route.NHType.via)
                for gw in conf.get_list('nexthops')
        ]

        return cls(action_name, dest, nexthops)


class ActionAddRoute(moduleapi.Action):
    """Add route action.

    Adds a route to the FIB.

    """

    _SettingsClass = ActionAddReplaceRouteSettings
    """Settings class for this action."""

    def execute(self, context):
        """Execute the action.

        Receives a moduleapi.ActionContext.

        """
        r = self.settings.route

        self.module.logger.info("adding route to %s via %s", r.dest, _nexthops_str(r.nexthops))
        self.module.fib.add_route(r)


class ActionReplaceRoute(moduleapi.Action):
    """Replace route action.

    Replaces a route in the FIB. If the route already exists, it is
    changed. Otherwise, it is added.

    """

    _SettingsClass = ActionAddReplaceRouteSettings
    """Settings class for this action."""

    def execute(self, context):
        """Execute the action.

        Receives a moduleapi.ActionContext.

        """
        r = self.settings.route

        self.module.logger.info("replacing route to %s via %s", r.dest, _nexthops_str(r.nexthops))
        self.module.fib.replace_route(r)


class RouteCheckSettings(config.Settings):
    """RouteCheck settings."""

    def __init__(self, dest, on_error, non_null=False, nexthops_any=None):
        """Initialize a RouteCheckSettings instance.

        dest should be netaddr.IPNetwork. on_error should be a list of
        action settings to execute in case of error.

        """
        super().__init__()

        if nexthops_any and not non_null:
            self.logger.info("route to %s has required nexthops, forcing non_null", dest)
            non_null = True

        self.rm = route.RouteMatch(dest=dest)
        self.on_error = on_error
        self.non_null = non_null
        self.nexthops_any = nexthops_any if nexthops_any is not None else []

    @classmethod
    def from_pyhocon(cls, conf, configurator):
        """Create RouteCheckSettings from a pyhocon ConfigTree.

        Returns a newly created instance of RouteCheckSettings. Raises
        config.ParseError in case of error.

        """
        dest = netaddr.IPNetwork(cls._get_conf(conf, 'dest'))

        non_null = conf.get_bool('non_null', default=False)

        nexthops_any = [
                netaddr.IPAddress(nh)
                for nh in conf.get_list('nexthops_any', default=[])
        ]

        on_error = [
            configurator.configure_action(subconf)
            for subconf in cls._get_conf(conf, 'on_error')
        ]

        return cls(dest, on_error, non_null, nexthops_any)


class FIBSettings(config.Settings):
    """FIB module settings."""

    def __init__(self, route_checks=None):
        """Initialize a FIBSettings instance."""
        super().__init__()

        self.route_checks = route_checks if route_checks is not None else []

    @classmethod
    def from_pyhocon(cls, conf, configurator):
        """Create FIBSettings from a pyhocon ConfigTree.

        Returns a newly created instance of FIBSettings. Raises
        config.ParseError in case of error.

        """
        route_checks = [
                RouteCheckSettings.from_pyhocon(subconf, configurator)
                for subconf in conf.get_list('route_checks', default=[])
        ]

        return cls(route_checks)


class FIBModuleAPI(moduleapi.ModuleAPI, metaclass=abc.ABCMeta):
    """Base class for FIB module APIs.

    This class cannot be imported directly; it must be subclassed by a
    specific FIB module, and the _create_fib method overriden for that FIB.

    """

    _SettingsClass = FIBSettings
    """Settings class for this API."""

    actions = {'add_route': ActionAddRoute, 'replace_route': ActionReplaceRoute}
    """Actions for this API, by name."""

    def __init__(self, settings):
        """Initialize the FIB module.

        Receives a FIBSettings object, containing the module's settings.

        """
        super().__init__(settings)

        self.settings = settings
        self.fib = self._create_fib()

    @staticmethod
    @abc.abstractmethod
    def _create_fib():
        """Create a FIB instance."""
        raise NotImplementedError()

    def run(self, dispatch):
        """Run any configured verifications and actions in this module."""

        status = moduleapi.ModuleRunStatus.ok

        for route_check in self.settings.route_checks:
            substatus = self.do_route_check(route_check, dispatch)
            status = max(status, substatus)

        return status

    def _route_check_failed(self, dispatch, route_check, error_reason):
        """Handle a failed route check.

        Logs a warning and executes the actions in route_check's on_error.
        Returns True if all actions succeed, False otherwise.

        """
        dest = route_check.rm.dest
        self.logger.warn("route_check to %s failed: %s", dest, error_reason)

        context = moduleapi.ActionContext(self.name,
                "route_check: route to {!s} {:s}".format(dest, error_reason))

        all_ok = True
        for settings in route_check.on_error:
            try:
                dispatch.execute_action(settings, context)
            except Exception as e:
                self.logger.error("while executing action %s: %s",
                        settings.action_name, e)
                all_ok = False

        return all_ok

    def do_route_check(self, route_check, dispatch):
        """Do a route check.

        Receives a RouteCheckSettings object, containing the settings for
        the route check. Returns a ModuleRunStatus.

        """
        dest = route_check.rm.dest
        self.logger.debug("checking route to %s", dest)

        r = self.fib.get_route_to(route_check.rm)

        MRS = moduleapi.ModuleRunStatus

        if r is None:
            ok = self._route_check_failed(dispatch, route_check, "not found")
            return MRS.check_failed if ok else MRS.action_error

        self.logger.debug("route found, via %s", _nexthops_str(r.nexthops))

        if route_check.non_null:
            if r.is_null:
                ok = self._route_check_failed(dispatch, route_check,
                        "{:s}, should be non-null".format(r.rt_type.name))
                return MRS.check_failed if ok else MRS.action_error
            else:
                self.logger.debug("route to %s is non-null, as expected", dest)

        if route_check.nexthops_any:
            for nh in r.nexthops:
                if nh.gw in route_check.nexthops_any:
                    self.logger.debug("route to %s via expected NH %s", dest, nh.gw)
                    break
            else:
                error_reason = "via {:s}, not in [{:s}]".format(
                        _nexthops_str(r.nexthops),
                        ', '.join(str(ip) for ip in route_check.nexthops_any))
                ok = self._route_check_failed(dispatch, route_check, error_reason)
                return MRS.check_failed if ok else MRS.action_error

        self.logger.info("route_check to %s check satisfied", dest)

        return MRS.ok


API = FIBModuleAPI

# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
