#! /usr/bin/env python3

# NetForeman - making sure your network is running smoothly
# Copyright (C) 2016 Israel G. Lugo
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

class Email(email.mime.text.MIMEText):
    def __init__(self, text, from_, to, subject, date=None):

        super().__init__(text, _charset='utf-8')

        self['From'] = from_
        self['To'] = to
        self['Subject'] = subject
        if date is None:
            self['Date'] = email.utils.formatdate()
        else:
            self['Date'] = email.utils.formatdate(date)
        self['Message-ID'] = email.utils.make_msgid('netforeman')
        self['User-Agent'] = 'NetForeman {:s}'.format(version.__version__)


def send(msg, server, port=25, username=None, password=None):
    sender = smtplib.SMTP(server, port)
    sender.send_message(msg)
    sender.quit()
