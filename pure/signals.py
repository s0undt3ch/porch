# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2013 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    pure.signals
    ~~~~~~~~~~~~

    PuRe related signals
'''
# pylint: disable=C0103

# Import 3rd-party libs
from blinker import Namespace

# Get a reference to a name-spaced signal
signal = Namespace().signal

configuration_loaded = signal(
    'configuration-loaded',
    'Emitted once the configuration has been loaded.'
)

application_configured = signal(
    'application-configured',
    'Emitted once the application has been configured.'
)