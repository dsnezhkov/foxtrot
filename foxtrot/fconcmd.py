import time
import threading
import json
import queue
from socket import gethostname

from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from pygments.token import Token

from foxtrot.fconstyle import AgentStyle
from curtsies.fmtfuncs import red, blue, green, yellow


class FConCommander:
    def __init__(self, config, fx):
        self.config = config
        self.fx = fx
        self.data_q = queue.Queue(2)
        self.out_watch = None


    # Style Based Configuration
    def _get_bottom_toolbar_tokens(self, cli):

        if 'recv_watch' in self.config and self.config['recv_watch'] != 0:
            recv_watch_interval = self.config['recv_watch']
        else:
            recv_watch_interval = 0

        tcontent='[{}] - K:{} NS:{} TSN:{} SOA:{} CI:{}'.format(
            self.config['role'], self.config['key'], self.config['nssrv'],
            self.config['tsigname'], self.config['domain'], recv_watch_interval
        )

        return [
            (Token.Toolbar, tcontent ),
        ]

    def _get_prompt_tokens(self, cli):

        return [
            (Token.Username, self.config['agent'].decode('utf-8')),
            (Token.At,       '@'),
            (Token.Host,     gethostname()),
            (Token.Marker,    '> '),
        ]

    def _get_rprompt_tokens(self, cli):

        tb_time = time.strftime("%d %b %Y %H:%M:%S", time.gmtime())
        return [
            (Token.DTime, tb_time),
        ]

    def _get_title(self):
        return 'Foxtrot'

    def do_loop(self): # use console facilities
        history = InMemoryHistory()
        gh_completer_client = WordCompleter(
            ['show', 'ident', 'peek', 'clear', 'reset', 'set', 'recv', 'csend', 'dsend'],
            ignore_case=True, match_middle=True)

        while True:
            result=None
            try:
                result = prompt(completer=gh_completer_client,
                  style=AgentStyle, vi_mode=True,
                  enable_history_search=True,
                  reserve_space_for_menu=4,
                  complete_while_typing=True,
                  display_completions_in_columns=True,
                  get_rprompt_tokens=self._get_rprompt_tokens,
                  wrap_lines=True,
                  get_prompt_tokens=self._get_prompt_tokens,
                  get_bottom_toolbar_tokens=self._get_bottom_toolbar_tokens,
                  enable_system_bindings=True,
                  get_title=self._get_title,
                  history = history,
                  auto_suggest=AutoSuggestFromHistory(),
                  patch_stdout=True)
            except KeyboardInterrupt:
                self.fx.flogger.warning("^D to exit")
            except EOFError:
                return

            if not result:
                pass
            else:
                cmdargs=""
                tokens = result.split(' ')

                if len(tokens) > 0:
                    cmd = tokens[0] # get command
                    if cmd == 'clear':
                        clear()
                    elif cmd == 'help':
                        print("""
                              System: Alt-!
                              Exit: Ctlr-D
                              Skip: Ctrl-C
                              Search: Vi mode standard
                              """)

                    elif cmd == 'ident':
                        self.do_ident()

                    elif cmd == 'show':
                        self.do_show()

                    elif cmd == 'peek':
                        self.do_peek()

                    elif cmd == 'reset':
                        self.do_reset()

                    elif cmd == 'recv':
                        if len(tokens) == 2:
                            comm = tokens[1]
                            self.do_recv(comm)
                        else:
                            self.do_recv()

                    elif cmd == 'csend':
                        if len(tokens) > 1:
                            self.do_csend(tokens[1:])
                        else:
                            print("Need commands")

                    elif cmd == 'dsend':
                        if len(tokens) > 1:
                            self.do_dsend(tokens[1])
                        else:
                            print("Need path to data file")

                    elif cmd == 'set':
                        self.do_set(result)
                    else:
                        print("Unsupported Command")
                else:
                    print("Invalid Command")

    def _dumpconf(self, obj):
        for k, v in obj.items():
            print('%s : %s' % (k, v))

    def do_ident(self):
        print(self.fx.agent_ident())

    def do_show(self):
        print(self.fx.agent_show())

    def do_peek(self):
        print(self.fx.agent_peek())

    def do_reset(self):
        self.fx.agent_reset()

    def do_set(self, result):
        print(result)
        cmdargs = result.split(' ', 1)  # get arguments
        if len(cmdargs) > 1 and '=' in result:  # Args exist
            self.fx.flogger.debug("Cmdargs: " + ' '.join(cmdargs))
            k, v = ''.join(cmdargs[1:]).split('=')  # get key value arguments
            print("{} : {}".format(k, v))
            self.config[k] = v
        else:
            self._dumpconf(self.config)

    def do_csend(self, command=None):
        """Send Command"""
        if command[0] is not "":
            cmd = " ".join(command)
            acmd = cmd.encode('ascii')
            self.fx.action_send_ocmd(acmd)
            return

    def do_dsend(self, fpath=None):
        if fpath is not None:
            dfh = self.fx.fpath2fh(fpath)
            self.fx.action_send_data_file(dfh)
        else:
            print("Path to file missing.")

    def do_recv(self, comm=None):
        """Real Time Recv output monitoring"""
        self.fx.flogger.debug("Command {} received".format(comm))

        if comm is None:
            self.fx.action_recv()
            return

        if comm == 'poll':
            if self.out_watch is None or (not self.out_watch.isAlive()):
                self.out_watch = threading.Thread(target=self.recv_watcher)
                self.out_watch.daemon = True
                self.out_watch.do_run = True
                self.data_q.queue.clear()
                print("Starting recv polling")
                self.fx.flogger.info("Request to start recv thread ".format(comm))
                self.out_watch.start()
            else:
                print("Recv polling already running")
                self.fx.flogger.warning("Recv polling already running({})".
                      format(self.out_watch.ident))

        elif comm == 'nopoll':
            print("Stopping recv polling")
            self.fx.flogger.info("Request to stop poll thread ({})".format(comm))
            if self.out_watch is not None and self.out_watch.isAlive():
                self.out_watch.do_run = False
                self.out_watch.join()

                # reset watch
                # TODO: Implement generic handler for all resets
                # self.config['recv_watch'] = 0
                self.do_set("set recv_watch=2") # use console facilities
            else:
                print("Recv polling not active")
                self.fx.flogger.warning("Recv polling not active")

    def recv_watcher(self):
        t = threading.currentThread()
        self.fx.flogger.debug("Recv polling thread init {}".format(t))

        # How often to check DNS
        # TODO: Abstract this time to a parameter
        self.config['recv_watch'] = 5

        while getattr(t, "do_run", True):
            self.fx.flogger.debug("Polling Record for jobs")
            peek_data = self.fx.agent_peek()
            jpeek_data = json.loads(peek_data)

            # New request found
            if self.config['role'] == 'master':
                if jpeek_data['t'].lower() == 's' and jpeek_data["s"].upper() == 'W':
                    self.fx.action_recv()

            if self.config['role'] == 'slave':
                if jpeek_data['t'].lower() == 'q' and jpeek_data["s"].upper() == 'J':
                    print(blue("== Incoming request =="))
                    self.fx.action_recv()

            # TODO: implement timer
            time.sleep(self.config['recv_watch'])
        self.fx.flogger.debug("Recv polling thread exit {}".format(t))
        return


