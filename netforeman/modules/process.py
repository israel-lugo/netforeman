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


"""Process handling."""

import pwd

import psutil

from netforeman import config
from netforeman import moduleapi


class ProcessCheckSettings(config.Settings):
    """ProcessCheck settings."""

    def __init__(self, basename, on_error, cmdline=None, user=None):
        """Initialize a ProcessCheckSettings instance.

        basename should be a str. on_error should be a list of action
        settings to execute in case of error. cmdline, if specified, should
        be a list of str. user if specified should be a pwd.struct_passwd.

        """
        super().__init__()

        self.basename = basename
        self.cmdline = cmdline
        self.user = user
        self.on_error = on_error

    @staticmethod
    def _get_passwd(uid_or_name):
        """Get a pwd.struct_passwd for a given UID or username.

        Raises KeyError if the user doesn't exist.

        """
        if isinstance(uid_or_name, int):
            passwd = pwd.getpwuid(uid_or_name)
        else:
            passwd = pwd.getpwnam(uid_or_name)

        return passwd

    @classmethod
    def from_pyhocon(cls, conf, configurator):
        """Create ProcessCheckSettings from a pyhocon ConfigTree.

        Returns a newly created instance of ProcessCheckSettings. Raises
        config.ConfigError in case of error.

        """
        basename = cls._get_conf(conf, 'basename')
        cmdline_raw = conf.get('cmdline', default=None)

        if isinstance(cmdline_raw, str):
            # split by words
            cmdline = cmdline_raw.split()
        else:
            # assume it's a list, manually split by the user e.g. because
            # of spaces in arguments
            cmdline = cmdline_raw

        user_raw = conf.get('user', default=None)
        user = cls._get_passwd(user_raw) if user_raw is not None else None

        on_error = [
                configurator.configure_action(subconf)
                for subconf in cls._get_conf(conf, 'on_error')
        ]

        return cls(basename, on_error, cmdline, user)


class ProcessSettings(config.Settings):
    """Process module settings."""

    def __init__(self, process_checks=None):
        """Initialize a ProcessSettings instance."""
        super().__init__()

        self.process_checks = process_checks if process_checks is not None else []

    @classmethod
    def from_pyhocon(cls, conf, configurator):
        """Create ProcessSettings from a pyhocon ConfigTree.

        Returns a newly created instance of ProcessSettings. Raises
        config.ConfigError in case of error.

        """

        process_checks = [
            ProcessCheckSettings.from_pyhocon(subconf, configurator)
            for subconf in conf.get_list('process_checks', default=[])
        ]

        return cls(process_checks)


# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
