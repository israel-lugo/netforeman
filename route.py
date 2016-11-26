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


"""Route table entry."""


import socket
import enum # Python 3.4 and above

import pyroute2
import netaddr


# TODO: Create a dictionary of routes by dest, to quickly spot IPv6 multipath
# routes, and store them in our own RouteTable object.


class NHType(enum.Enum):
    """Next-hop types."""
    # XXX: Linux defines this, when can we find it? Only example I know of
    # is when doing "ip route get"
    # local = 1
    connected = 2
    via = 3


class NextHop:
    """Nexthop within a route."""

    def __init__(self, gw, ifname, nh_type):
        """Initialize a NextHop instance."""

        self.gw = gw
        self.ifname = ifname
        self.nh_type = nh_type

    def __str__(self):
        """Convert to string."""

        s = "dev {:s}".format(self.ifname)

        if self.nh_type == NHType.via:
            s = "via {:s} {:s}".format(str(self.gw), s)

        return s

    @classmethod
    def from_mpath_msg(cls, ipr, msg):
        """Create a NextHop from an rtnetlink multipath message."""

        gw_str = msg.get_attr('RTA_GATEWAY')
        gw = netaddr.IPAddress(gw_str) if gw_str is not None else None

        oif_idx = msg['oif']
        ifname = get_ifname(ipr, oif_idx)
        
        nh_type = cls._guess_nh_type(gw)

        return cls(gw, ifname, nh_type)

    @classmethod
    def from_rtmsg(cls, ipr, msg):
        """Create a NextHop from an rtnetlink message."""

        gw_str = msg.get_attr('RTA_GATEWAY')
        gw = netaddr.IPAddress(gw_str) if gw_str is not None else None

        oif_idx = msg.get_attr('RTA_OIF')
        ifname = get_ifname(ipr, oif_idx)

        nh_type = cls._guess_nh_type(gw)

        return cls(gw, ifname, nh_type)

    @staticmethod
    def _guess_nh_type(gw):
        """Guess the nexthop type based on the gateway."""

        # XXX: This is a rather crude guess
        if gw is None:
            nh_type = NHType.connected
        else:
            nh_type = NHType.via

        return nh_type



class Route:
    """Route to a certain destination.

    Can contain multiple nexthops (multipath route).

    """
    def __init__(self, family, dest, destlen, nexthops, metric, proto, rt_type):
        """Initialize a Route instance."""

        self.family = self._validate_family(family)
        self.dest = dest
        self.destlen = destlen
        self.nexthops = nexthops
        self.metric = metric
        self.proto = proto
        self.rt_type = rt_type

        if self.destlen == 0:
            if ((family == socket.AF_INET and dest != netaddr.IPNetwork("0.0.0.0/0"))
                    or (family == socket.AF_INET6 and dest != netaddr.IPNetwork("::/0"))):
                raise ValueError("destlen == 0 and dest isn't a default route")

        self.is_default = (destlen == 0)
        self.multipath = len(nexthops) > 1

    def __str__(self):
        """Convert to a string."""

        s = str(self.dest) if not self.is_default else "default"

        if self.multipath:
            s = "{:s} proto {:s}".format(s, self.proto)
            nh_str = ''.join([ "\n\tnexthop " + str(nh) for nh in self.nexthops ])
            s += nh_str
        else:
            s = "{:s} {:s} proto {:s}".format(s, str(self.nexthops[0]), self.proto)

        return s


    @classmethod
    def from_rtnl_msg(cls, ipr, rtnl_msg):
        """Create a Route from an rtnetlink message."""

        family = cls._validate_family(rtnl_msg['family'])

        destlen = rtnl_msg['dst_len']
        if destlen == 0:
            dest = cls._default_network(family)
        else:
            dest_str = "{:s}/{:d}".format(rtnl_msg.get_attr('RTA_DST'), destlen)
            dest = netaddr.IPNetwork(dest_str)

        # Linux only sets RTA_MULTIPATH on IPv4. IPv6 multipath routes are seen
        # as separate, unrelated routes, which happen to have the same dst.
        nh_msgs = rtnl_msg.get_attr('RTA_MULTIPATH')
        if nh_msgs is not None:
            nexthops = [NextHop.from_mpath_msg(ipr, msg) for msg in nh_msgs]
        else:
            nexthops = [NextHop.from_rtmsg(ipr, rtnl_msg)]

        # XXX: This seems to not exist on IPv4, will be None when family == AF_INET
        metric = rtnl_msg.get_attr('RTA_PRIORITY')

        proto = cls._get_proto_name(rtnl_msg['proto'])

        rt_type = cls._get_rt_typename(rtnl_msg['type'])

        return cls(family, dest, destlen, nexthops, metric, proto, rt_type)

    @staticmethod
    def _validate_family(family):
        """Validate that family is a proper value.

        Returns a canonical family value. Raises ValueError if family is an
        invalid value.

        """
        if family not in (socket.AF_INET, socket.AF_INET6):
            raise ValueError("invalid family {:d}".format(family))

        return family

    @staticmethod
    def _default_network(family):
        """Return the default network for the specified family."""

        if family == socket.AF_INET:
            return netaddr.IPNetwork("0.0.0.0/0")
        else:
            return netaddr.IPNetwork("::/0")

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

    return [Route.from_rtnl_msg(ipr, msg) for msg in nl_routes]


if __name__ == '__main__':
    ipr = pyroute2.IPRoute()

    rt4 = get_routes(ipr, socket.AF_INET)
    rt6 = get_routes(ipr, socket.AF_INET6)

    for r in rt4:
        print(r)

    for r in rt6:
        print(r)

