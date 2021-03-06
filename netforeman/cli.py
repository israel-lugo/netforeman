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
import logging
import sys

from netforeman import dispatch
from netforeman import moduleapi

from netforeman.version import __version__


__all__ = [ 'main' ]


DEFAULT_LOG_LEVEL = logging.INFO
"""Default level for the root logger."""


def create_logger():
    """Set up logging and return a logger object."""

    root_logger = logging.getLogger()
    root_logger.setLevel(DEFAULT_LOG_LEVEL)

    stderr = logging.StreamHandler()
    stderr.setLevel(logging.DEBUG)
    stderr.setFormatter(logging.Formatter("%(asctime)s %(name)s: %(levelname)s: %(message)s"))

    root_logger.addHandler(stderr)

    return logging.getLogger('netforeman')


def parse_args():
    """Parse command-line arguments.

    Returns a populated namespace with all arguments and their values.

    """
    parser = argparse.ArgumentParser(
            description="Making sure your network is running smoothly.")

    parser.add_argument('-d', '--debug', action='store_true',
            help='enable debug verbosity')

    parser.add_argument('-V', '--version', action='version',
            version="NetForeman %s" % __version__)

    parser.add_argument('config_file', metavar='CONFIG-FILE',
            help='configuration file')

    args = parser.parse_args()

    return args

def main():
    """Main program function."""

    logger = create_logger()

    args = parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        dispatcher = dispatch.Dispatch(args.config_file)
    except dispatch.DispatchError as e:
        logger.error("aborting: %s", str(e))
        return 1

    status = dispatcher.run()

    if status == moduleapi.ModuleRunStatus.ok:
        logger.info("all done, terminating...")
    elif status == moduleapi.ModuleRunStatus.check_failed:
        logger.warn("check(s) failed, all actions executed successfully")
    elif status == moduleapi.ModuleRunStatus.action_error:
        logger.error("check(s) failed, at least one action had an error")
    else:
        logger.error("finished with unknown errors")

    return int(status)


if __name__ == '__main__':
    sys.exit(main())


# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
