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


def nexthop_from_mpath_msg(ipr, msg):
    """Create a NextHop from an rtnetlink multipath message."""

    gw_str = msg.get_attr('RTA_GATEWAY')
    gw = netaddr.IPAddress(gw_str) if gw_str is not None else None

    oif_idx = msg['oif']
    ifname = get_ifname(ipr, oif_idx)

    nh_type = _guess_nh_type(gw)

    return route.NextHop(gw, ifname, nh_type)

def nexthop_from_rtmsg(ipr, msg):
    """Create a NextHop from an rtnetlink message."""

    gw_str = msg.get_attr('RTA_GATEWAY')
    gw = netaddr.IPAddress(gw_str) if gw_str is not None else None

    oif_idx = msg.get_attr('RTA_OIF')
    ifname = get_ifname(ipr, oif_idx)

    nh_type = _guess_nh_type(gw)

    return route.NextHop(gw, ifname, nh_type)

def _guess_nh_type(gw):
    """Guess the nexthop type based on the gateway."""

    # XXX: This is a rather crude guess
    if gw is None:
        nh_type = route.NHType.connected
    else:
        nh_type = route.NHType.via

    return nh_type


def route_from_rtnl_msg(ipr, rtnl_msg):
    """Create a Route from an rtnetlink message."""

    family = route.Route.validate_family(rtnl_msg['family'])

    destlen = rtnl_msg['dst_len']
    if destlen == 0:
        dest = _default_network(family)
    else:
        dest_str = "{:s}/{:d}".format(rtnl_msg.get_attr('RTA_DST'), destlen)
        dest = netaddr.IPNetwork(dest_str)

    # Linux only sets RTA_MULTIPATH on IPv4. IPv6 multipath routes are seen
    # as separate, unrelated routes, which happen to have the same dst.
    nh_msgs = rtnl_msg.get_attr('RTA_MULTIPATH')
    if nh_msgs is not None:
        nexthops = [nexthop_from_mpath_msg(ipr, msg) for msg in nh_msgs]
    else:
        nexthops = [nexthop_from_rtmsg(ipr, rtnl_msg)]

    # XXX: This seems to not exist on IPv4, will be None when family == AF_INET
    metric = rtnl_msg.get_attr('RTA_PRIORITY')

    proto = _get_proto_name(rtnl_msg['proto'])

    rt_type = _get_rt_typename(rtnl_msg['type'])

    return route.Route(family, dest, destlen, nexthops, metric, proto, rt_type)

def _default_network(family):
    """Return the default network for the specified family."""

    if family == socket.AF_INET:
        return netaddr.IPNetwork("0.0.0.0/0")
    else:
        return netaddr.IPNetwork("::/0")

def _get_rt_typename(typenum):
    """Get the route type name from its number.

    Raises KeyError if the route type is unknown.

    """
    return pyroute2.netlink.rtnl.rt_type[typenum]

def _get_proto_name(protonum):
    """Get the source protocol name from its number.

    Raises KeyError if the protocol is unknown.

    """
    return pyroute2.netlink.rtnl.rt_proto[protonum]

def get_ifname(ipr, index):
    return ipr.link("get", index=index)[0].get_attr('IFLA_IFNAME')


def print_nl_routes(ipr, rt_table):
    for rt in rt_table:
        prefix_len = rt['dst_len']
        if prefix_len == 0:
            dst = 'default'
        else:
            dst = "{:s}/{:d}".format(rt.get_attr('RTA_DST'), prefix_len)

        gw = rt.get_attr('RTA_GATEWAY')
        ifname = get_ifname(ipr, rt.get_attr('RTA_OIF'))

        if gw is not None:
            via = " via {:s}".format(gw)
        else:
            via = ""

        print("{:s}{:s} dev {:s}".format(dst, via, ifname))


def get_netlink_routes(ipr, family):
    return ipr.get_routes(family=family, table=254)


def get_routes(ipr, family):
    nl_routes = get_netlink_routes(ipr, family)

    return [route_from_rtnl_msg(ipr, msg) for msg in nl_routes]


if __name__ == '__main__':
    ipr = pyroute2.IPRoute()

    rt4 = get_routes(ipr, socket.AF_INET)
    rt6 = get_routes(ipr, socket.AF_INET6)

    for r in rt4:
        print(r)

    for r in rt6:
        print(r)

