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


"""Linux interface."""

import socket
import netaddr
import pyroute2

import route


class LinuxFIBInterface(route.FIBInterface):
    def __init__(self):
        self.ipr = pyroute2.IPRoute()

    def get_routes(self, family):
        nl_routes = self.ipr.get_routes(family=family, table=254)

        return [self._route_from_rtnl_msg(msg) for msg in nl_routes]

    def _route_from_rtnl_msg(self, rtnl_msg):
        """Create a Route from an rtnetlink message."""

        family = rtnl_msg['family']
        destlen = rtnl_msg['dst_len']
        if destlen == 0:
            dest = route.Route.default_network(family)
        else:
            dest_str = "{:s}/{:d}".format(rtnl_msg.get_attr('RTA_DST'), destlen)
            dest = netaddr.IPNetwork(dest_str)

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

        rt_type = self._get_rt_typename(rtnl_msg['type'])

        return route.Route(family, dest, destlen, nexthops, metric, proto, rt_type)

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
        ifname = self._get_ifname(oif_idx)

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
            import errno
            if e.code == errno.ENODEV:
                return None

        return iface.get_attr('IFLA_IFNAME')

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
    def _get_rt_typename(typenum):
        """Get the route type name from its number.

        Raises KeyError if the route type is unknown.

        """
        return pyroute2.netlink.rtnl.rt_type[typenum]

    @staticmethod
    def _get_proto_name(protonum):
        """Get the source protocol name from its number.

        Raises KeyError if the protocol is unknown.

        """
        return pyroute2.netlink.rtnl.rt_proto[protonum]

