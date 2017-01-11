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


from netforeman import config


class Dispatch:
    def __init__(self, config_filename):
        """Initialize a dispatcher."""

        self.config = config.Configurator(config_filename)

        self.config.load_modules()

    def run(self):
        """Run module behavior."""

        for modinfo in self.config.loaded_modules:
            modinfo.api.run(self)

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

        try:
            api = self.config.modules_by_name[module_name].api
        except KeyError as e:
            raise config.ParseError("no such module '{:s}' in action definition".format(module_name))

        if relative_action not in api.actions:
            raise NameError("action '{:s}' not defined in module '{:s}'".format(action, module_name))

        api.actions[relative_action](action_conf, context)


# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
