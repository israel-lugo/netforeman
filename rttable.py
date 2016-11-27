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


class RoutingTable:
    def __init__(self, routes=None):
        """Initialize a RoutingTable.

        Changes the routes *in place*, to aggregate nexthops to the same
        path.

        """
        self.routes = []
        self.routes_by_dest = {}

        if routes is not None:
            for r in routes:
                r_ = self.routes_by_dest.get(r.dest)

                if r_ is None:
                    self.routes.append(r)
                    self.routes_by_dest[r.dest] = r
                else:
                    r_.add_nexthops(r.nexthops)

    def __iter__(self):
        return self.routes.__iter__()

    def get_route_for(self, addr):
        """Get longest matching route for an address.

        Returns the most specific Route object that matches the specified
        address, or None if none exists.

        """
        # netaddr.smallest_matching_cidr sorts the routes and does a linear
        # search; this isn't very efficient and probably shouldn't be used
        # for a full Internet table. We should either 1) implement a trie, or
        # 2) precalculate several dicts based on the prefixlens that occur
        # in the table, then, for each prefixlen starting from the longest,
        # lookup the address bitwise-and with the netmask for that
        # prefixlen. Space-speed tradeoff.
        prefix = netaddr.smallest_matching_cidr(addr, self.routes_by_dest)

        return self.routes_by_dest[prefix] if prefix is not None else None
