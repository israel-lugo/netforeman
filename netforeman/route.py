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

    def __eq__(self, other):
        """self == other

        Returns True if self is equal to other in all non-None fields.

        """
        return ((self.gw is None or self.gw == other.gw)
                and (self.ifname is None or self.ifname == other.ifname)
                and (self.nh_type is None or self.nh_type == other.nh_type))

    def __ne__(self, other):
        """self != other"""
        return not self.__eq__(other)


class Route:
    """Route to a certain destination.

    Can contain multiple nexthops (multipath route).

    """
    def __init__(self, family, dest, destlen, nexthops, metric, proto, rt_type):
        """Initialize a Route instance."""

        self.family = self.validate_family(family)

        if (self.family, dest.version) not in ((socket.AF_INET, 4), (socket.AF_INET6, 6)):
            raise ValueError("family doesn't match dest's IP version")

        prefixlen = self.prefixlen_from_dest(dest)
        if prefixlen != destlen:
            raise ValueError("destlen ({:d}) doesn't match dest's prefix ({:d})".format(
                destlen, prefixlen))

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
        self.multipath = (len(nexthops) > 1)

    def __eq__(self, other):
        """self == other"""
        return (self.family == other.family
                and self.dest == other.dest
                and self.destlen == other.destlen
                and self.nexthops == other.nexthops
                and self.metric == other.metric
                and self.proto == other.proto
                and self.rt_type == other.rt_type)

    def __ne__(self, other):
        """self != other"""
        return not self.__eq__(other)

    def add_nexthops(self, nexthops):
        """Add nexthops from a list.

        No check is made for duplicate nexthops; if a new nexthop matches
        an already existing one, both will be stored.

        """
        self.nexthops += nexthops

        self.multipath = True

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

    @staticmethod
    def validate_family(family):
        """Validate that family is a proper value.

        Returns a canonical family value. Raises ValueError if family is an
        invalid value.

        """
        if family not in (socket.AF_INET, socket.AF_INET6):
            raise ValueError("invalid family {:d}".format(family))

        return family

    @staticmethod
    def prefixlen_from_dest(dest):
        """Get the prefix from an IPAddress or an IPNetwork.

        If dest is an IPNetwork, returns its prefixlen. If dest is an
        IPAddress, returns either 32 or 128, depending on whether it's IPv4
        or IPv6.

        """
        # assume dest is an IPNetwork and get its prefix
        prefixlen = getattr(dest, 'prefixlen', None)

        if prefixlen is None:
            # dest must be an IPAddress
            prefixlen = 32 if dest.version == 4 else 128

        return prefixlen

    @classmethod
    def default_network(cls, family):
        """Return the default network for the specified family."""
        family = cls.validate_family(family)

        if family == socket.AF_INET:
            return netaddr.IPNetwork("0.0.0.0/0")
        else:
            return netaddr.IPNetwork("::/0")


class RouteMatch(Route):
    """Route subclass that accepts incomplete parameters, for matching."""

    def __init__(self, family, dest=None, destlen=None, nexthops=None, metric=None, proto=None, rt_type=None):
        """Initialize a RouteMatch instance."""

        self.family = self.validate_family(family)

        # these checks only make sense if dest was provided
        if dest is not None:
            if (self.family, dest.version) not in ((socket.AF_INET, 4), (socket.AF_INET6, 6)):
                raise ValueError("family doesn't match dest's IP version")

            prefixlen = self.prefixlen_from_dest(dest)

            if destlen is None:
                destlen = prefixlen
            elif prefixlen != destlen:
                raise ValueError("destlen ({:d}) doesn't match dest's prefix ({:d})".format(
                    destlen, prefixlen))

            if self.destlen == 0:
                if ((family == socket.AF_INET and dest != netaddr.IPNetwork("0.0.0.0/0"))
                        or (family == socket.AF_INET6 and dest != netaddr.IPNetwork("::/0"))):
                    raise ValueError("destlen == 0 and dest isn't a default route")

        if nexthops is None:
            nexthops = []

        self.dest = dest
        self.destlen = destlen
        self.nexthops = nexthops
        self.metric = metric
        self.proto = proto
        self.rt_type = rt_type

        self.is_default = (destlen == 0)
        self.multipath = (len(nexthops) > 1)

    def __eq__(self, other):
        """self == other

        Returns True if self is equal to other in all non-None fields.

        """
        return (self.family == other.family
                and (self.dest is None or self.dest == other.dest)
                and (self.dest is None or self.destlen == other.destlen)
                and (not self.nexthops or self.nexthops == other.nexthops)
                and (self.metric is None or self.metric == other.metric)
                and (self.proto is None or self.proto == other.proto)
                and (self.rt_type is None or self.rt_type == other.rt_type))

    def __str__(self):
        """Convert to a string."""

        s = str(self.dest) if not self.is_default else "default"

        if self.multipath:
            s = "{:s} proto {:s}".format(s, str(self.proto))
            nh_str = ''.join([ "\n\tnexthop " + str(nh) for nh in self.nexthops ])
            s += nh_str
        else:
            nh = self.nexthops[0] if self.nexthops else None
            s = "{:s} {:s} proto {:s}".format(s, str(nh), str(self.proto))

        return s


