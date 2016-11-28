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


"""Routing table."""


import netaddr


class TCAM:
    """Ternary Content-Addressable Memory.

    Provides quick lookup access to existing routes. Can perform exact
    lookups or longest match.

    """

    def __init__(self):
        """Initialize an empty TCAM."""
        self.dests_by_len = {}

    def add(self, r):
        """Add a route to the TCAM."""
        destlen = r.destlen

        routes_by_dest = self.dests_by_len.get(destlen)

        if routes_by_dest is not None:
            routes_by_dest[r.dest] = r
        else:
            self.dests_by_len[destlen] = {r.dest: r}

    def get_exact(self, dest):
        """Lookup in the TCAM for an exact match for dest.

        dest must be a netaddr.IPNetwork object. Returns a Route object,
        or None if no exact match exists.

        """
        if not isinstance(dest, netaddr.IPNetwork):
            # we're hashing dest in dests_by_len; it needs to be the right
            # type otherwise we won't match anything
            raise TypeError("dest must be a netaddr.IPNetwork")

        try:
            routes_by_dest = self.dests_by_len[dest.prefixlen]

            r = routes_by_dest[dest]
        except KeyError:
            r = None

        return r

    def longest_match(self, dest):
        """Lookup in the TCAM for the longest match for dest.

        dest should be either a netaddr.IPAddress or a netaddr.IPNetwork.
        Returns a Route object, or None if no match exists.

        """
        if dest.version == 4:
            bits = 32
        elif dest.version == 6:
            bits = 128
        else:
            raise ValueError("dest.version must be either 4 or 6")

        # if dest has a prefixlen, make sure we only accept routes that can
        # contain it in its entirety
        maxlen = getattr(dest, 'prefixlen', bits)
        assert maxlen <= bits

        # get the IP from dest (if it's a network), or dest itself
        ip = getattr(dest, 'ip', dest)
        ip_str = str(ip)

        interesting_lens = filter(lambda x: x <= maxlen, self.dests_by_len)

        r = None
        for destlen in sorted(interesting_lens, reverse=True):
            truncated = netaddr.IPNetwork("{:s}/{:d}".format(ip_str, destlen),
                                          flags=netaddr.NOHOST)
            r = self.dests_by_len[destlen].get(truncated, None)
            if r is not None:
                break

        return r


class RoutingTable:
    def __init__(self, routes=None):
        """Initialize a RoutingTable.

        Changes the routes *in place*, to aggregate nexthops to the same
        path.

        """
        self.tcam = TCAM()
        self.routes = []

        if routes is not None:
            for r in routes:
                r_ = self.tcam.get_exact(r.dest)

                if r_ is None:
                    self.tcam.add(r)
                    self.routes.append(r)
                else:
                    r_.add_nexthops(r.nexthops)

    def __iter__(self):
        """Return an iterator over the routes."""

        return self.routes.__iter__()

    def get_route_for(self, dest):
        """Get longest matching route for an address or network.

        dest should be either a netaddr.IPAddress or a netaddr.IPNetwork.
        Returns the most specific Route object that matches dest, or None
        if none exists.

        """
        return self.tcam.longest_match(dest)


if __name__ == '__main__':
    import linux
    import socket

    fib = linux.LinuxRoutingInterface()

    rt4 = RoutingTable(fib.get_routes(socket.AF_INET))
    rt6 = RoutingTable(fib.get_routes(socket.AF_INET6))

    for r in rt4:
        print(r)

    for r in rt6:
        print(r)

