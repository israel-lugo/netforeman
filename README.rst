NetForeman
==========

|license|

Making sure your network is running smoothly.

NetForeman is your network's foreman: an advanced programmable network system
supervisor. It is meant to run on network infrastructure systems, such as
routers, for automatic monitoring and reacting to a wide array of situations.

The idea behind this program is to automate problem solving whenever possible.
You shouldn't have to stare at screens and graphs 24/7 to know that your
firewall's connection tracking table is almost full. When that happens, you
shouldn't have to manually go check the top 10 flow endpoints, to find out that
a single host is sourcing 1,000,000 flows to different IPs.

Likewise, you shouldn't have to check the routing table on 20 routers to find
out that your OSPF designated router is failing in a silent way, still sending
out hellos but no longer redistributing LSAs (the consequence being that both
the DR and BDR have a full table, but every other router is isolated from the
network).

NetForeman's mission is to help detect, diagnose and react to these sorts of
problems.


Features
--------

NetForeman supports both IPv4 and IPv6. It is currently work in progress, not
yet ready for production use. The following features are planned for now:

Verifications
.............

- Monitor the routing table (only Linux for now, but planning for being extensible)

  - The number of routes is within a certain range
  - There is a route for a certain prefix
  - The route for a certain prefix is through a specific nexthop

- Monitor running processes

  - A certain process is running

- Monitor connection tracking

  - The number of tracked connections doesn't exceed a certain limit

Actions
.......

Triggered by a verification failure:

- Insert routes
- Send emails
- Restart services
- Execute arbitrary scripts


Installing
----------

NetForeman requires Python3, and the following third-party modules:

- netaddr_
- pyhocon_
- pyroute2_


Contact
-------

NetForeman is developed by Israel G. Lugo <israel.lugo@lugosys.com>. Main
repository for cloning, submitting issues and/or forking is at
https://github.com/israel-lugo/netforeman


License
-------

Copyright (C) 2016 Israel G. Lugo <israel.lugo@lugosys.com>

NetForeman is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

NetForeman is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with NetForeman.  If not, see <http://www.gnu.org/licenses/>.


.. |license| image:: https://img.shields.io/badge/license-GPLv3+-blue.svg?maxAge=2592000
   :target: LICENSE
.. _netaddr: https://github.com/drkjam/netaddr
.. _pyhocon: https://github.com/chimpler/pyhocon
.. _pyroute2: https://github.com/svinota/pyroute2
