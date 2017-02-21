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

import os
import subprocess
import tempfile
import pwd
import locale

import psutil

from netforeman import config
from netforeman import moduleapi



def _parse_cmdline(cmdline_raw):
    """Parse a pyhocon cmdline option.

    cmdline_raw must be either a string (which will be split by
    whitespace), or a list of strings (which will be taken literally as a
    list of args), or None.

    Returns the cmdline as a list of strings (args).

    """
    if isinstance(cmdline_raw, str):
        # split by words
        cmdline = cmdline_raw.split()
    else:
        # assume it's a list, manually split by the user e.g. because
        # of spaces in arguments
        cmdline = cmdline_raw

    return cmdline


def _get_passwd(uid_or_name):
    """Get a pwd.struct_passwd for a given UID or username.

    Raises config.ConfigError if the user doesn't exist.

    """
    try:
        if isinstance(uid_or_name, int):
            passwd = pwd.getpwuid(uid_or_name)
        else:
            passwd = pwd.getpwnam(uid_or_name)
    except KeyError:
        raise config.ConfigError("user {!s} doesn't exist".format(uid_or_name))

    return passwd


class ActionExecuteSettings(moduleapi.ActionSettings):
    """Settings for ActionExecute."""

    def __init__(self, action_name, cmdline, user, on_output=None):
        """Initialize an ActionExecuteSettings instance.

        cmdline should be a list of str. user should be a
        pwd.struct_passwd. on_output, if specified, should be an instance
        of moduleapi.ActionListSettings, to be executed if the command
        gives out any output on stdout or stderr.

        """
        super().__init__(action_name)

        self.cmdline = cmdline
        self.user = user
        self.on_output = on_output

    @classmethod
    def from_pyhocon(cls, conf, configurator):
        """Create ActionExecuteSettings from a pyhocon ConfigTree."""

        action_name = cls._get_conf(conf, 'action')

        cmdline_raw = cls._get_conf(conf, 'cmdline')
        cmdline = _parse_cmdline(cmdline_raw)

        user_raw = cls._get_conf(conf, 'user')
        user = _get_passwd(user_raw)

        on_output_raw = cls._get_conf(conf, 'on_output', False)
        on_output = moduleapi.ActionListSettings.from_pyhocon(on_output_raw, configurator) \
                if on_output_raw else None

        return cls(action_name, cmdline, user, on_output)


class ActionExecute(moduleapi.Action):
    """Execute a process action."""

    _SettingsClass = ActionExecuteSettings
    """Settings class for this action."""

    MAX_DATA_READ = 4096
    """Maximum data to be read from the output of an executed process."""

    def set_user(self):
        """Change to the user specified in settings.

        Receives a pwd.struct_passwd. Changes the real user id, the
        effective user id and the saved user id to the uid of the specified
        user. Guarantees that the user ids have really been changed, or
        terminates the program otherwise. Works on GNU/Linux and a few
        other Unixes.

        This function is meant to be called from a child process, to change
        its user id before executing the new program.

        """
        # We are called by the subprocess module, already within the child
        # process. stdout and stderr have already been redirected. Any
        # logging output that is not direct to file/syslog, will end up in
        # the child's output.

        # Exceptions thrown here will prevent the child program from being
        # executed, and an subprocess.CalledProcessError exception from the
        # subprocess module.

        uid = self.settings.user.pw_uid
        try:
            os.setresuid(uid, uid, uid)
        except Exception as e:
            self.module.logger.error("unable to set user: %s", e)
            raise

        # be paranoid
        ruid, euid, suid = os.getresuid()
        if ruid != uid or euid != uid or suid != uid:
            self.module.logger.critical("changed UID but it didn't change (quitting for security)")
            raise RuntimeError()

    def execute(self, context):
        """Execute the action.

        Receives a moduleapi.ActionContext.

        """
        self.module.logger.info("executing %s as %s", self.settings.cmdline,
                self.settings.user.pw_name)

        if self.settings.on_output:
            self._execute_with_output(context)
        else:
            self._execute_without_output(context)

    def _execute_without_output(self, context):
        """Execute the command, throwing away its output."""
        subprocess.check_call(self.settings.cmdline,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT, close_fds=True,
                preexec_fn=self.set_user)

    def _execute_with_output(self, context):
        """Execute the command, and capture its output."""
        output_data = None
        with tempfile.TemporaryFile() as output:
            try:
                subprocess.check_call(self.settings.cmdline,
                        stdin=subprocess.DEVNULL, stdout=output,
                        stderr=subprocess.STDOUT, close_fds=True,
                        preexec_fn=self.set_user)
            finally:
                size = output.tell()
                if size:
                    output.seek(0)
                    output_data = output.read(self.MAX_DATA_READ)

        if output_data:
            # TODO: Deal with binary output somehow. For now we're just
            # converting to text and replacing what we can't decode.
            encoding = locale.getpreferredencoding()
            output_text = output_data.decode(encoding, "replace")

            print(output_text)


class ProcessCheckSettings(config.Settings):
    """ProcessCheck settings."""

    def __init__(self, basename, on_error, cmdline=None, user=None):
        """Initialize a ProcessCheckSettings instance.

        basename should be a str. on_error should be an instance of
        ActionListSettings to execute in case of error. cmdline, if
        specified, should be a list of str. user if specified should be a
        pwd.struct_passwd.

        """
        super().__init__()

        self.basename = basename
        self.cmdline = cmdline
        self.user = user
        self.on_error = on_error

    @classmethod
    def from_pyhocon(cls, conf, configurator):
        """Create ProcessCheckSettings from a pyhocon ConfigTree.

        Returns a newly created instance of ProcessCheckSettings. Raises
        config.ConfigError in case of error.

        """
        basename = cls._get_conf(conf, 'basename')

        cmdline_raw = conf.get('cmdline', default=None)
        cmdline = _parse_cmdline(cmdline_raw)

        user_raw = conf.get('user', default=None)
        user = _get_passwd(user_raw) if user_raw is not None else None

        on_error = moduleapi.ActionListSettings.from_pyhocon(
                cls._get_conf(conf, 'on_error'), configurator)

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


class ProcessModuleAPI(moduleapi.ModuleAPI):
    """Process module API."""

    _SettingsClass = ProcessSettings
    """Settings class for this API."""

    actions = {'execute': ActionExecute}
    """Actions for this API, by name."""

    def __init__(self, settings):
        """Initialize the Process module.

        Receives a ProcessSettings object, containing the module's settings.

        """
        super().__init__(settings)

        self.settings = settings

    def run(self, dispatch):
        """Run any configured verifications and actions in this module."""

        status = moduleapi.ModuleRunStatus.ok

        for process_check in self.settings.process_checks:
            substatus = self.do_process_check(process_check, dispatch)
            status = max(status, substatus)

        return status

    def _process_check_failed(self, dispatch, process_check, error_reason):
        """Handle a failed process check.

        Logs a warning and executes the actions in process_check's
        on_error. Returns True if all actions succeed, False otherwise.

        """
        basename = process_check.basename
        self.logger.warn("process_check for %s failed: %s", basename, error_reason)

        context = moduleapi.ActionContext(self.name,
                "process_check: process {!s}: {:s}".format(basename, error_reason))

        action_list = moduleapi.ActionList(self.logger, process_check.on_error)
        all_ok = action_list.run(dispatch, context)

        return all_ok

    def do_process_check(self, process_check, dispatch):
        """Do a process check.

        Receives a ProcessCheckSettings object, containing the settings for
        the process check. Returns a ModuleRunStatus.

        """
        basename = process_check.basename
        cmdline = process_check.cmdline
        user = process_check.user

        self.logger.debug("checking '%s' processes", basename)

        name_matches = [p for p in psutil.process_iter() if p.name() == basename]

        MRS = moduleapi.ModuleRunStatus

        if not name_matches:
            ok = self._process_check_failed(dispatch, process_check, "no match for basename")
            return MRS.check_failed if ok else MRS.action_error

        self.logger.debug("found %d match(es) for '%s'", len(name_matches), basename)

        if cmdline is not None:
            cmdline_matches = [p for p in name_matches if p.cmdline() == cmdline]
            if not cmdline_matches:
                ok = self._process_check_failed(dispatch, process_check, "no match for cmdline")
                return MRS.check_failed if ok else MRS.action_error

            self.logger.debug("%s match(es) for cmdline '%s'", len(cmdline_matches), cmdline)

        if user is not None:
            user_matches = [p for p in cmdline_matches if p.username() == user.pw_name]
            if not user_matches:
                ok = self._process_check_failed(dispatch, process_check, "no match for user")
                return MRS.check_failed if ok else MRS.action_error

            self.logger.debug("%s match(es) for user '%s'", len(user_matches), user.pw_name)

        return MRS.ok


API = ProcessModuleAPI

# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
