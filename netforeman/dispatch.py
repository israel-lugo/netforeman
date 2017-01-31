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


"""Dispatch module."""

import logging

from netforeman import config


class DispatchError(Exception):
    """Error while dispatching."""
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class Dispatch:
    def __init__(self, config_filename):
        """Initialize a dispatcher.

        Receives the name of the configuration file to parse.

        """
        self.logger = logging.getLogger('netforeman.dispatch')
        self.config = config.Configurator(config_filename)

        ok = self.config.load_modules()
        if not ok:
            raise DispatchError("errors while loading modules")

    def run(self):
        """Run module behavior."""

        errors = False
        for api in self.config.loaded_apis:
            try:
                self.logger.debug("running module %s", api.name)
                api.run(self)
            except config.ParseError as e:
                self.logger.error("config error in module '%s': %s", api.name, str(e))
                errors = True

        return not errors

    def execute_action(self, settings, context):
        """Execute an action.

        Receives an instance of moduleapi.ActionSettings and an
        ActionContext.

        """
        action_name = settings.action_name

        action_class, api = self.config.resolve_action(action_name)

        # api should only be None if the module isn't loaded, in which case
        # we shouldn't have gotten here
        assert api is not None

        action = action_class(api, settings)
        action.execute(context)


# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
