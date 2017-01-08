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

import netforeman.moduleapi


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


class EmailModuleAPI(netforeman.moduleapi.ModuleAPI):
    """Email module API."""

    def __init__(self, conf):
        """Initialize the email module.

        Receives a pyhocon.config_tree.ConfigTree object, containing the
        module's config tree.

        """
        self.from_address = self._get_conf(conf, 'from_address')
        self.to_address = self._get_conf(conf, 'to_address')
        self.server = self._get_conf(conf, 'server')
        self.port = self._get_conf(conf, 'port')
        self.username = self._get_conf(conf, 'username', False)
        self.password = self._get_conf(conf, 'password', False)

    @property
    def actions(self):
        """Get the email module's actions."""

        return {'sendmail': self.sendmail}

    @classmethod
    def get_module_args(cls):
        """Get the names of the module arguments.

        This is a dictionary of {name: required}, where name is the name of
        the argument, and required is True if the argument must be present.

        """
        return cls._module_args

    def sendmail(self, subject, text=''):
        """Send an email message."""

        msg = _Email(text, self.from_address, self.to_address, subject)

        sender = smtplib.SMTP(self.server, self.port)
        sender.send_message(msg)
        sender.quit()


API = EmailModuleAPI

