
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


"""API definition for all NetForeman modules."""


import logging
import abc

from netforeman.config import ParseError


class ActionContext:
    """Context information for an action.

    Useful for the dispatcher to resolve relative actions, and also for the
    modules to pass a message to an action.

    """

    def __init__(self, calling_module, message):
        self.calling_module = calling_module
        self.message = message


class Action(metaclass=abc.ABCMeta):
    """Base class for actions.

    Subclasses MUST define a class attribute _SettingsClass, which should
    be the appropriate subclass of config.Settings for that Action
    subclass. This will be used by settings_from_pyhocon.

    """

    def __init__(self, module, settings):
        """Initialize an Action.

        module should be a loaded instance of the module to which this
        action belongs. settings should be an instance of the appropriate
        Settings subclass for this action.

        Subclasses SHOULD call the original method, for common
        initialization.

        """
        self.module = module
        self.settings = settings

    @abc.abstractmethod
    def execute(self, context):
        """Execute the action.

        Receives an ActionContext.

        """
        pass

    @classmethod
    def settings_from_pyhocon(cls, conf):
        """Get settings for this action.

        Receives a pyhocon.config_tree.ConfigTree and returns an
        appropriate subclass of config.Settings. Raises ParseError in case
        of error.

        Subclasses of Action MUST appropriately define the class attribute
        _SettingsClass.

        """
        return cls._SettingsClass.from_pyhocon(conf)


class ModuleAPI(metaclass=abc.ABCMeta):
    """Base class for the API of all NetForeman modules.

    Modules must override a set of abstract methods and properties. Also,
    they may provide callbacks, known as actions.

    The actions must be available in the actions property, in the form of a
    dictionary of name: function. The function is to receive 2 arguments:
    conf (an instance of pyhocon.config_tree.ConfigTree) and context (an
    ActionContext).

    """

    @abc.abstractmethod
    def __init__(self, conf):
        """Initialize the module API.

        Receives a pyhocon.config_tree.ConfigTree object, containing the
        module's config tree.

        Subclasses SHOULD call the original method for initializing common
        attributes such as logging.

        This method is only for initialization and should not execute any
        independent behavior, such as user-configured checks and actions.
        The run method should be used for that.

        """
        self.logger = logging.getLogger("netforeman.%s" % self.name)

    @property
    def name(self):
        """Get the module's name.

        This is the module's basename, as used for importing.

        """
        return self.__module__.rpartition('.')[2]

    @property
    @abc.abstractmethod
    def actions(self):
        """Get the module's actions."""
        return {}

    # This method need not be overriden if the module doesn't do anything
    # by itself (e.g. it only exists to provide callable actions).
    def run(self, dispatch):
        """Run any configured verifications and actions in this module.

        Receives an instance of the module dispatch. This may be used by
        the module to execute actions.

        This method should be overriden by modules with their own
        independent behavior, e.g. modules that perform user-configured
        verifications or actions by themselves. Modules which only provide
        callable actions (e.g. sendmail) need not override this.

        """
        pass

# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
