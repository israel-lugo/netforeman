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


class Route:
    """Route to a certain destination.

    Can contain multiple nexthops (multipath route).

    """
    def __init__(self, family, dest, destlen, nexthops, metric, proto, rt_type):
        """Initialize a Route instance."""

        self.family = self.validate_family(family)

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


class FIBError(Exception):
    """Error from a FIB interface."""

    def __init__(self, msg, orig=None):
        self.msg = msg
        self.orig=orig

    def __str__(self):
        return self.msg


class FIBInterface:
    """Interface to an underlying FIB.

    This is a base class for specific FIB interfaces. It must be
    subclassed, and its methods must be implemented.

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

