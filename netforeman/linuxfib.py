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


"""Linux interface."""

import socket
import errno
import netaddr
import pyroute2

from netforeman import route
from netforeman import fibinterface



# Mapping of Netlink route types to route.RouteType. We use this so we
# don't have to rely on RouteType values matching Netlink order. We can
# change this to a dict if we ever need to.
_nl_rttype_to_rttype = [
    route.RouteType.unspec,
    route.RouteType.unicast,
    route.RouteType.local,
    route.RouteType.broadcast,
    route.RouteType.anycast,
    route.RouteType.multicast,
    route.RouteType.blackhole,
    route.RouteType.unreachable,
    route.RouteType.prohibit,
    route.RouteType.throw,
    route.RouteType.nat,
    route.RouteType.xresolve
]


class LinuxFIBInterface(fibinterface.FIBInterface):
    """Interface to an underlying Linux FIB."""

    def __init__(self):
        self.ipr = pyroute2.IPRoute()

    def get_routes(self, family):
        """Get routes from the underlying FIB."""
        nl_routes = self.ipr.get_routes(family=family, table=254)

        return [self._route_from_rtnl_msg(msg) for msg in nl_routes]

    def add_route(self, r):
        """Add a route to the FIB.

        Raises fibinterface.FIBError in case of error (such as no
        permissions, route already exists, and so on).

        """
        self._route_cmd("add", r)

    def change_route(self, r):
        """Change an existing route in the FIB.

        Raises fibinterface.FIBError in case of error (such as no
        permissions, route doesn't exist, and so on).

        """
        self._route_cmd("change", r)

    def delete_route(self, r):
        """Delete an existing route from the FIB.

        Raises fibinterface.FIBError in case of error (such as no
        permissions, route doesn't exist, and so on).

        """
        self._route_cmd("del", r)

    def get_route_to(self, rm):
        """Get a route from the FIB matching the specified route.

        Raises fibinterface.FIBError in case of error (such as no
        permissions, route doesn't exist, and so on).

        """
        if rm.is_default:
            # Netlink's "get" doesn't work on default routes, see issue #8
            default_routes = self.get_default_routes(rm.family)
            if not default_routes:
                # XXX we should distinguish between error and no route
                raise fibinterface.FIBError("no default routes exist for IPv%d"
                        % (4 if rm.family == socket.AF_INET else 6))

            # we're supposed to return _a_ route
            return default_routes[0]

        try:
            match = self._route_cmd("get", rm)[0]

        except fibinterface.FIBError as e:
            # Unreachable, blackhole or prohibited routes give an error on
            # lookup; check if that's the case and resolve it ourselves.
            # Issue #5. Testing returned ENETUNREACH on some systems,
            # EHOSTUNREACH on others. See:
            #   man ip-route(8)
            #   linux/net/ipv4/fib_semantics.c:fib_props
            #   linux/net/ipv6/fib6_rules.c:fib6_rule_action() ?
            if e.orig.code in (errno.ENETUNREACH, errno.EHOSTUNREACH,
                               errno.EACCES, errno.EINVAL):
                # EINVAL could actually mean some other weird error
                routes = self.matching_routes_to(rm.dest)
                if not routes:
                    # no route exists now (race condition, or other error)
                    raise fibinterface.FIBError("no route exists for %s"
                            % rm.dest)

                # return most specific route (should be the null one)
                return routes[0]
            else:
                # unknown error, re-raise
                raise

        return self._route_from_rtnl_msg(match)

    def get_default_routes(self, family):
        """Get the list of default routes for the specified family.

        The list will be empty if no default routes exist. Raises
        fibinterface.FIBError in case of error (such as no permissions, and
        so on).

        """
        nl_routes = self.ipr.get_routes(family=family, table=254)

        return [self._route_from_rtnl_msg(msg)
                for msg in nl_routes
                if msg['dst_len'] == 0]

    def matching_routes_to(self, dest):
        """Get the list of all routes matching the specified dest.

        dest should be a netaddr.IPNetwork. The list of routes will be
        sorted from most specific (longest) to least specific (shortest).
        The list will be empty if there are no routes matching dest.

        This function does the route matching in user space, as opposed to
        getting the routes from the kernel. It is the only way to deal with
        blackhole or unreachable IPv4 routes on Linux, as asking the kernel
        to resolve would result in an error.

        """
        nl_routes = self.ipr.get_routes(
                family=route.Route.family_from_dest(dest),
                table=254)

        destlen = dest.prefixlen

        return sorted(
            [self._route_from_rtnl_msg(msg)
             for msg in nl_routes
             if msg['dst_len'] == 0     # include default route, which has no RTA_DST
                or (msg['dst_len'] <= destlen
                    and dest
                        in netaddr.IPNetwork("%s/%d" % (msg.get_attr('RTA_DST'), msg['dst_len'])))
            ],
            key=lambda r: r.destlen,    # sort by prefix length (specificity)
            reverse=True)

    # TODO: Create a get_all_routes_to() method, that returns all routes to
    # a certain destination (or rm, not sure). Will be necessary for
    # a route check (on FIBModuleAPI), that makes sure that the nexthops
    # are exactly as specified.

    def replace_route(self, r):
        """Replace a route in the FIB.

        If the route exists, it is changed. If it doesn't exist, a new one
        is created. Raises fibinterface.FIBError in case of error (such as
        no permissions, and so on).

        """
        self._route_cmd("replace", r)

    def _route_cmd(self, cmd, r):
        """Run a route command on the FIB.

        cmd must be one of "add", "del", "get", "change" or "replace".

        Returns the result of the command. Raises fibinterface.FIBError in
        case of error (such as no permissions, route already exists, and so
        on).

        """
        if cmd not in ("add", "del", "get", "change", "replace"):
            raise ValueError("invalid cmd '{:s}'".format(cmd))

        kwargs = self._route_to_dict(r)
        try:
            result = self.ipr.route(cmd, **kwargs)
        except pyroute2.netlink.exceptions.NetlinkError as e:
            raise fibinterface.FIBError(e.args[1], e)

        return result

    def _route_to_dict(self, r):
        """Convert a Route to a dict of its non-None attributes

        The attributes are formatted for use in a Netlink message.

        """
        d = {}

        if r.dest is not None: d['dst'] = str(r.dest)
        if r.rt_type is not None: d['type'] = r.rt_type.name
        if r.proto is not None: d['proto'] = r.proto
        if r.multipath:
            d['multipath'] = [self._nexthop_to_dict(nh) for nh in r.nexthops]
        elif r.nexthops:
            d.update(self._nexthop_to_dict(r.nexthops[0]))

        return d

    def _nexthop_to_dict(self, nh):
        """Convert a NextHop to a dict of its non-None attributes."""
        d = {}

        if nh.gw is not None: d['gateway'] = str(nh.gw)
        if nh.ifname is not None: d['oif'] = self._get_ifidx(nh.ifname)

        return d

    def _route_from_rtnl_msg(self, rtnl_msg):
        """Create a Route from an rtnetlink message."""

        family = rtnl_msg['family']
        destlen = rtnl_msg['dst_len']
        if destlen == 0:
            dest = route.Route.default_network(family)
        else:
            dest_str = "{:s}/{:d}".format(rtnl_msg.get_attr('RTA_DST'), destlen)
            dest = netaddr.IPNetwork(dest_str)

        # make sure Netlink's idea of the protocol family equals our own
        assert family == route.Route.family_from_dest(dest)

        # Linux only sets RTA_MULTIPATH on IPv4. IPv6 multipath routes are seen
        # as separate, unrelated routes, which happen to have the same dst.
        nh_msgs = rtnl_msg.get_attr('RTA_MULTIPATH')
        if nh_msgs is not None:
            nexthops = [self._nexthop_from_mpath_msg(msg) for msg in nh_msgs]
        else:
            nexthops = [self._nexthop_from_rtmsg(rtnl_msg)]

        # XXX: This seems to not exist on IPv4, will be None when family == AF_INET
        metric = rtnl_msg.get_attr('RTA_PRIORITY')

        proto = self._get_proto_name(rtnl_msg['proto'])

        rt_type = self._get_rt_type(rtnl_msg['type'])

        return route.Route(dest, destlen, nexthops, metric, proto, rt_type)

    def _nexthop_from_mpath_msg(self, msg):
        """Create a NextHop from an rtnetlink multipath message."""

        gw_str = msg.get_attr('RTA_GATEWAY')
        gw = netaddr.IPAddress(gw_str) if gw_str is not None else None

        oif_idx = msg['oif']
        ifname = self._get_ifname(oif_idx)

        nh_type = self._guess_nh_type(gw)

        return route.NextHop(gw, ifname, nh_type)

    def _nexthop_from_rtmsg(self, msg):
        """Create a NextHop from an rtnetlink message."""

        gw_str = msg.get_attr('RTA_GATEWAY')
        gw = netaddr.IPAddress(gw_str) if gw_str is not None else None

        oif_idx = msg.get_attr('RTA_OIF')
        ifname = self._get_ifname(oif_idx) if oif_idx is not None else None

        nh_type = self._guess_nh_type(gw)

        return route.NextHop(gw, ifname, nh_type)

    def _get_ifname(self, index):
        """Get the name of an interface.

        Returns the name of the interface with the specified index, or None
        if none exists.

        """
        try:
            iface = self.ipr.link("get", index=index)[0]
        except pyroute2.netlink.exceptions.NetlinkError as e:
            if e.code == errno.ENODEV:
                return None

        return iface.get_attr('IFLA_IFNAME')

    def _get_ifidx(self, ifname):
        """Get the index of an interface.

        Returns the index of the interface with the specified name, or None
        if none exists.

        """
        iflist = self.ipr.link_lookup(ifname=ifname)

        return iflist[0] if iflist else None

    @staticmethod
    def _guess_nh_type(gw):
        """Guess the nexthop type based on the gateway."""

        # XXX: This is a rather crude guess
        if gw is None:
            nh_type = route.NHType.connected
        else:
            nh_type = route.NHType.via

        return nh_type

    @staticmethod
    def _get_rt_type(typenum):
        """Get the route.RouteType from a Netlink route type.

        Raises a subclass of LookupError if typenum is unknown.

        """
        # we reserve the right to change this to a dict in the future;
        # hence, we say we raise the base class of IndexError and KeyError
        return _nl_rttype_to_rttype[typenum]

    @staticmethod
    def _get_proto_name(protonum):
        """Get the source protocol name from its number.

        Raises KeyError if the protocol is unknown.

        """
        return pyroute2.netlink.rtnl.rt_proto[protonum]



class LinuxFIBModuleAPI(fibinterface.FIBModuleAPI):
    """Linux FIB module API."""
    @staticmethod
    def _create_fib():
        """Create a FIB instance."""
        return LinuxFIBInterface()

API = LinuxFIBModuleAPI
# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
