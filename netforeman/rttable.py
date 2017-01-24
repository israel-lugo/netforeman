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


"""Routing table."""


import importlib
import socket

import netaddr

import netforeman.moduleapi


class TCAM:
    """Ternary Content-Addressable Memory.

    Provides quick lookup access to existing routes. Can perform exact
    lookups or longest match.

    """

    # This is implemented as a dict of destlen, where the values are dicts
    # of dest. In other words, the routes are first indexed by prefix
    # length, and within a certain prefix length they are indexed by
    # destination.

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

    def remove(self, r):
        """Remove a route from the TCAM.

        Raises KeyError if no such route exists.

        """
        destlen = r.destlen
        dest = r.dest

        # to avoid having to search every single route
        if destlen is None:
            raise ValueError("can only remove from TCAM routes with destlen")

        # to avoid slow linear searches within the routes of a certain len
        if dest is None:
            raise ValueError("can only remove from TCAM routes with dest")

        routes_by_dest = self.dests_by_len[destlen]

        existing_r = routes_by_dest[dest]

        # compare r to existing_r and not the other way around, since r may
        # be a RouteMatch (we want to use r's __eq__())
        if r != existing_r:
            raise KeyError("existing route for {:s} differs from supplied one".format(str(dest)))

        del routes_by_dest[dest]

        if not routes_by_dest:
            # no more routes with that destlen
            del self.dests_by_len[destlen]

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


class RoutingTableModuleAPI(netforeman.moduleapi.ModuleAPI):
    """Routing table module API."""

    def __init__(self, conf):
        """Initialize the routing table module.

        Receives a pyhocon.config_tree.ConfigTree object, containing the
        module's config tree.

        """
        # TODO: Finish this. Parse the whole subtree.

        fib_name = self._get_conf(conf, 'fib')
        fib_module = self._load_fib_module(fib_name)

        self.fib = fib_module.FIBInterface()

        self.rt4 = RoutingTable(self.fib.get_routes(socket.AF_INET))
        self.rt6 = RoutingTable(self.fib.get_routes(socket.AF_INET6))


    @property
    def actions(self):
        """Get the routing table module's actions."""
        return {'add_route': self.add_route}

    @staticmethod
    def _load_fib_module(name):
        """Load a FIB module."""
        return importlib.import_module("{:s}.{:s}".format(__package__, name))



API = RoutingTableModuleAPI



if __name__ == '__main__':
    from netforeman import linuxfib

    fib = linuxfib.LinuxFIBInterface()

    rt4 = RoutingTable(fib.get_routes(socket.AF_INET))
    rt6 = RoutingTable(fib.get_routes(socket.AF_INET6))

    for r in rt4:
        print(r)

    for r in rt6:
        print(r)

# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
