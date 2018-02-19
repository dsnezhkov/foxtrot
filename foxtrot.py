#!/usr/bin/env python

import sys
from foxtrot.flib import Foxtrot
from foxtrot.helpers import Configurator


def main():
    # Process command line arguments
    Configurator.parseArgs()

    # Setup configuration bindings
    config = Configurator.getConfig()
    Configurator.printConfig()

    # Configure logging facilities
    logger = Configurator.getLogger()
    fx = Foxtrot(config, logger)

    # Process directives
    if config['args'].action == 'console':
        fx.action_console()

    if ((config['args'].action == 'agent' and
             (config['args'].operation != 'generate' and config['args'].operation != 'delete')) or
            (config['args'].action == 'recv') or
            (config['args'].action == 'send')):

        # Check if agent exists. If not - bail out.
        fx.agent_check()

    # Agent management and data inspection actions
    if config['args'].action == 'agent':

        if config['args'].operation == 'show':
            print(fx.agent_show())

        if config['args'].operation == 'peek':
            print(fx.agent_peek())

        if config['args'].operation == 'ident':
            fx.agent_ident()

        if config['args'].operation == 'generate':
            fx.agent_generate()

        if config['args'].operation == 'delete':
            fx.agent_delete()

        if config['args'].operation == 'reset':
            fx.agent_reset()

    # Send and receive actions
    if config['args'].action == 'send':

        if config['args'].operation == 'dfile':
            if config['args'].dfpath is not None:
                fx.action_send_data_file(config['args'].dfpath)
            else:
                fx.flogger.error("Data file path is missing ")
                sys.exit(2)

        if config['args'].operation == 'ocmd':

            if (config['args'].ofpath is not None) or (config['args'].ocmd is not None):
                if config['args'].ofpath is not None:
                    fx.action_send_ocmd_file(config['args'].ofpath)
                else:
                    fx.action_send_ocmd(config['args'].ocmd.encode('ascii'))
            else:
                fx.flogger.error("Command not specified or Data file path is missing ")
                sys.exit(2)

        if config['args'].operation == 'mcmd':
            if config['args'].mcmd is not None:
                fx.action_send_mcmd(config['args'].ocmd.encode('ascii'))

    if config['args'].action == 'recv':
        config['allow_exec'] = True
        fx.action_recv()


if __name__ == '__main__':
    main()
