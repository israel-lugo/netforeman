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


"""Email sending."""

import smtplib
import email.mime.text
import email.utils

from netforeman import version
from netforeman import config
from netforeman import moduleapi


class _Email(email.mime.text.MIMEText):
    def __init__(self, text, from_address, to_address, subject, date=None):

        super().__init__(text, _charset='utf-8')

        self['From'] = from_address
        self['To'] = to_address
        self['Subject'] = subject
        if date is None:
            self['Date'] = email.utils.formatdate()
        else:
            self['Date'] = email.utils.formatdate(date)
        self['Message-ID'] = email.utils.make_msgid('netforeman')
        self['User-Agent'] = 'NetForeman {:s}'.format(version.__version__)


class EmailSettings(config.Settings):
    """Email module settings."""

    _PORT = 25
    _DEFAULT_SUBJECT = "Email from NetForeman"

    def __init__(self, from_address, to_address, server, port=_PORT,
            default_subject=_DEFAULT_SUBJECT, username=None,
            password=None):
        """Initialize an EmailSettings instance."""
        super().__init__()

        self.from_address = from_address
        self.to_address = to_address
        self.server = server

        try:
            self.port = int(port)
        except ValueError:
            raise config.ConfigError("invalid port value '%s'" % str(port))

        self.default_subject = default_subject
        self.username = username
        self.password = password

    @classmethod
    def from_pyhocon(cls, conf, configurator):
        """Create EmailSettings from a pyhocon ConfigTree.

        Returns a newly created instance of EmailSettings. Raises
        config.ConfigError in case of error.

        """
        from_address = cls._get_conf(conf, 'from_address')
        to_address = cls._get_conf(conf, 'to_address')
        server = cls._get_conf(conf, 'server')
        port = conf.get('port', cls._PORT)
        default_subject = conf.get('default_subject', cls._DEFAULT_SUBJECT)
        username = cls._get_conf(conf, 'username', False)
        password = cls._get_conf(conf, 'password', False)

        return cls(from_address, to_address, server, port, default_subject,
                username, password)


class ActionSendEmailSettings(moduleapi.ActionSettings):
    """ActionSendEmail settings."""

    def __init__(self, action_name, text=None, subject=None):
        """Initialize settings for ActionSendEmail.

        text will be formatted using str.format(). There are named
        arguments available for replacement: {module} and {message}.
        Respectively, these are the name of the calling module, and the
        message from that module.

        If text is None or not provided, a default value will be used. If
        subject is None or not provided, the Email module's default subject
        will be used.

        """
        if action_name != "email.sendmail":
            # should never happen if our caller uses Dispatch resolution
            raise config.ConfigError("action name '{!s}', should be email.sendmail".format(action_name))

        super().__init__(action_name)

        if text is None:
            text = ("This is an automated email, sent from NetForeman.\n"
                    "\n"
                    "It was triggered by the {module} module.\n"
                    "\n"
                    "Message:\n"
                    "\n"
                    "{message}\n")

        # make sure text is valid for formatting
        try:
            text.format(module="", message="")
        except (ValueError, LookupError) as e:
            raise config.ConfigError("invalid value for text: {!s}".format(e))

        self.text = text
        self.subject = subject

    @classmethod
    def from_pyhocon(cls, conf, configurator):
        """Create ActionSendEmailSettings from a pyhocon ConfigTree."""

        action_name = cls._get_conf(conf, 'action')
        subject = conf.get('subject', default=None)
        text = conf.get('text', default=None)

        return cls(action_name, text, subject)


class ActionSendEmail(moduleapi.Action):
    """Send email action."""

    _SettingsClass = ActionSendEmailSettings
    """Settings class for this action."""

    def execute(self, context):
        """Execute the action.

        Receives a moduleapi.ActionContext.

        """
        self.module.logger.info("sending email, triggered by %s", context.calling_module)

        text = self.settings.text.format(
                module=str(context.calling_module),
                message=str(context.message))

        subject = (self.settings.subject
                    if self.settings.subject is not None
                    else self.module.settings.default_subject)

        msg = _Email(text, self.module.settings.from_address, self.module.settings.to_address, subject)

        sender = smtplib.SMTP(self.module.settings.server, self.module.settings.port)
        sender.send_message(msg)
        sender.quit()


class EmailModuleAPI(moduleapi.ModuleAPI):
    """Email module API."""

    _SettingsClass = EmailSettings
    """Settings class for this API."""

    actions = {'sendmail': ActionSendEmail}
    """Actions for this API, by name."""

    def __init__(self, settings):
        """Initialize the email module.

        Receives a EmailSettings object, containing the module's settings.

        """
        super().__init__(settings)

        self.settings = settings

        self.logger.debug("loaded, server %s, target %s",
                self.settings.server, self.settings.to_address)


API = EmailModuleAPI

# vim: set expandtab smarttab shiftwidth=4 softtabstop=4 tw=75 :
