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
        for modinfo in self.config.loaded_modules:
            try:
                self.logger.debug("running module %s", modinfo.api.name)
                modinfo.api.run(self)
            except config.ParseError as e:
                self.logger.error("config error in module '%s': %s", modinfo.name, str(e))
                errors = True

        return not errors

    def execute_action(self, action_conf, context):
        """Execute an action.

        action_conf is an instance of pyhocon.config_tree.ConfigTree. It
        must contain an "action" key, which is the name of the action to
        execute.

        If the action is a full dotted path, e.g. module.action, the action
        from the corresponding module will be executed. If the action is a
        relative path (without dots), the action from the calling module
        will be executed.

        """
        action = action_conf.get_string('action')

        module_name, _, relative_action = action.rpartition('.')

        if not module_name:
            module_name = context.calling_module

        self.logger.debug("executing action %s.%s, triggered by %s", module_name,
                relative_action, context.calling_module)

        try:
            api = self.config.modules_by_name[module_name].api
        except KeyError:
            raise config.ParseError("no such module '{:s}' in action definition".format(module_name))

        # TODO: Actions are classes now. Instantiate the action, give it
        # the API (because it may need it), and call its execute method.

        if relative_action not in api.actions:
            raise config.ParseError("action '{:s}' not defined in module '{:s}'".format(action, module_name))

        api.actions[relative_action](action_conf, context)


# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
