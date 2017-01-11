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


"""Main CLI user interface."""


import argparse

from netforeman import dispatch

from netforeman.version import __version__


__all__ = [ 'main' ]


def parse_args():
    """Parse command-line arguments.

    Returns a populated namespace with all arguments and their values.

    """
    parser = argparse.ArgumentParser(
            description="Making sure your network is running smoothly.")

    parser.add_argument('-V', '--version', action='version',
            version="NetForeman %s" % __version__)

    parser.add_argument('config_file', metavar='CONFIG-FILE',
            help='configuration file')

    args = parser.parse_args()

    return args


def main():
    """Main program function."""

    args = parse_args()

    # TODO: Catch errors. Create logger.

    dispatcher = dispatch.Dispatch(args.config_file)

    dispatcher.run()


if __name__ == '__main__':
    main()


# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
