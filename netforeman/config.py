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


"""Configuration parser."""

import abc
import logging
import importlib

import pyhocon


class ConfigError(Exception):
    """Error while parsing configuration."""
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class Configurable:
    """Mix-in class (trait) for all configurable classes.

    Descendants of Configurable gain a classmethod settings_from_pyhocon,
    which receives a pyhocon ConfigTree and returns an instance of the
    appropriate Settings subclass.

    Descendants MUST define a class attribute _SettingsClass, which will be
    used by settings_from_pyhocon to determine which Settings subclass to
    create.

    """
    @classmethod
    def settings_from_pyhocon(cls, conf, configurator):
        """Get settings for this class.

        Receives a pyhocon.config_tree.ConfigTree and a Configurator for
        name resolution while configuring nested objects. Returns an
        appropriate subclass of config.Settings, as per cls._SettingsClass.

        """
        return cls._SettingsClass.from_pyhocon(conf, configurator)


class Settings(metaclass=abc.ABCMeta):
    """Base class for the settings of all NetForeman modules.

    Subclasses MUST override the __init__ method with appropriate
    arguments. They SHOULD, however, call the original __init__ for common
    initialization. Subclasses MUST also override classmethod from_pyhocon.

    """

    @abc.abstractmethod
    def __init__(self):
        """Initialize a settings instance.

        Subclasses SHOULD call the original method for initializing common
        attributes such as logging.

        """
        self.logger = logging.getLogger('netforeman.settings')

    @classmethod
    @abc.abstractmethod
    def from_pyhocon(cls, conf, configurator):
        """Create an instance of settings from a pyhocon ConfigTree."""
        raise NotImplementedError

    @staticmethod
    def _get_conf(conf, name, required=True):
        """Get a value from a pyhocon.config_tree.ConfigTree.

        If the value is missing and required is True, raises a ConfigError
        exception. If the value is missing and required is False, returns
        None.

        """
        value = conf.get(name, None)
        if value is None and required:
            raise ConfigError("missing required argument '{:s}'".format(name))

        return value


class ModuleInfo:
    """Information about a loaded module."""

    def __init__(self, name, module, api):
        self.name = name
        self.module = module
        self.api = api


class Configurator:

    def __init__(self, filename):
        """Initializes a Configurator by parsing a configuration file.

        Receives the name of the configuration file. Raises ConfigError in
        case of error.

        """
        self.filename = filename

        self.logger = logging.getLogger('netforeman.config')
        self.logger.debug("reading configuration file '%s'", filename)

        try:
            self.conf = pyhocon.ConfigFactory.parse_file(filename)
        except pyhocon.exceptions.ConfigException as e:
            raise ConfigError(str(e))

        self.logger.debug("finished reading configuration file")

    def load_modules(self):
        """Load configured modules.

        Returns True if all modules loaded without error, False otherwise.

        """
        try:
            modules_to_load = self.conf['modules']
        except pyhocon.exceptions.ConfigMissingException as e:
            self.logger.error("missing mandatory section 'modules'")
            return False

        errors = False

        # useful to run the APIs in the order they were declared
        self.loaded_apis = []

        # useful to resolve actions for modules as they are being
        # configured (and therefore not instantiated)
        self.module_api_classes_by_name = {}

        # useful to run actions, they need a loaded API
        self.module_apis_by_name = {}

        for name in modules_to_load:
            if name in self.module_api_classes_by_name:
                self.logger.warning("ignoring duplicate entry for module '%s', already loaded", name)
                continue

            self.logger.debug("loading module '%s'", name)

            try:
                if name not in self.conf:
                    raise ConfigError("missing required section '{:s}'".format(module_name))

                config_tree = self.conf.get_config(name)

                API = self._get_module_api(name)
                self.module_api_classes_by_name[name] = API

                # settings may call resolve_action for its own actions;
                # module_api_classes_by_name (above) must already contain
                # the API class
                settings = API.settings_from_pyhocon(config_tree, self)
                api = API(settings)

                self.module_apis_by_name[name] = api
                self.loaded_apis.append(api)
            except ConfigError as e:
                self.logger.error("module '%s': %s", name, str(e))
                errors = True

        return not errors

    @staticmethod
    def _get_module_api(name):
        """Get the API class for the specified module.

        Dynamically loads the Python module and returns its subclass of
        moduleapi.ModuleAPI.

        """
        module = importlib.import_module("{:s}.modules.{:s}".format(__package__, name))

        return module.API

    def resolve_action(self, action_name):
        """Resolve an action by name.

        Receives an action's name, in the format module.action (e.g.
        "email.sendmail"). Relative action names are not allowed.

        Returns the tuple (action_class, api). That is, the Action
        subclass, and the loaded instance of the module's API.

        api will be None if the API is not instantiated yet (i.e. this
        function was called from within the module's settings parser, or
        there was a previous error while instantiating said module).

        Raises ConfigError in case of error (e.g. action not found).

        """
        module_name, _, action_basename = action_name.rpartition('.')

        # We don't allow relative names; it would be too complicated for
        # cases like linuxfib, which inherits almost everything from
        # fibinterface but is actually a different module. At configure
        # time, only dispatch or configurator know the current module.
        # Would require special casing the FIB settings and subsettings in
        # linuxfib just for this, or having to pass around the module name
        # in *every* configurable object. Not worth it.

        if not module_name:
            raise ConfigError("missing module name in action definition {:s}".format(action_name))

        if not action_basename:
            raise ConfigError("missing action name in action definition {:s}".format(action_name))

        try:
            # load from the class, as the API may not be instantiated yet
            api_class = self.module_api_classes_by_name[module_name]
        except KeyError:
            raise ConfigError("no such module '{:s}' in action definition".format(module_name))

        if action_basename not in api_class.actions:
            raise ConfigError("action '{:s}' not defined in module '{:s}'".format(action_name, module_name))

        action_class = api_class.actions[action_basename]

        api = self.module_apis_by_name.get(module_name, None)

        return (action_class, api)

    def configure_action(self, conf):
        """Configure an action.

        Receives an instance of pyhocon.config_tree.ConfigTree. It must
        contain an "action" key, which is the name of the action to
        execute.

        Returns an appropriate subclass of Settings for that action.

        """
        action_name = conf.get_string('action')

        action_class = self.resolve_action(action_name)[0]

        self.logger.debug("configuring action %s", action_name)

        return action_class.settings_from_pyhocon(conf, self)


# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
