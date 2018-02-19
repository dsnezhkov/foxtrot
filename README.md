# Foxtrot C2 


 C&C Infrastructure to deliver files and shuttle command execution instructions 
 between an external actor and an internal agent, over Firefox Send service,  
 with a command channel over DNS.

![Architecture diagram](/docs/Foxtrot-Arch.png)

### Usage

```
usage: foxtrot.py [--help] --agent [AGENT] --tsigname [TSIGNAME] --tsigrdata
                  [TSIGRDATA] --nserver [NSERVER] --domain [DOMAIN]
                  [--ffservice FFSERVICE] [--verbose {info,debug}] --role
                  {master,slave}
                  <action: send|recv|console|agent> [action options] ...

                
                C&C Infrastructure to deliver files and shuttle command execution instructions 
					 between an external actor and an internal agent, over Firefox Send service,  
                with a command channel over DNS.

                More information https://github.com/dsnezhkov/foxtrot/wiki 
                

positional arguments:
  <action: send|recv|console|agent> [action options]
                        Valid actions: send|recv

optional arguments:
  --help                Foxtrot Help
  --ffservice FFSERVICE
  --verbose {info,debug}
                        Verbosity level. Default: info
  --role {master,slave}
                        Role of the agent.

Required parameters:
  --agent [AGENT]       Agent id
  --tsigname [TSIGNAME]
                        TSIG name and Key
  --tsigrdata [TSIGRDATA]
                        TSIG data file
  --nserver [NSERVER]   Name Server IP
  --domain [DOMAIN]     Domain

<ACTION:  'send'>
usage: foxtrot.py send [-h] --operation {dfile,ocmd,mcmd} [--dfpath [DFPATH]]
                       [--ocmd OCMD] [--ofpath [OFPATH]] [--mcmd MCMD]

optional arguments:
  -h, --help            show this help message and exit
  --operation {dfile,ocmd,mcmd}
                        dfile: send data file for download as data; ocmd: send
                        command instruction for execution be agent, mcmd: send
                        internal command instruction for agent
  --dfpath [DFPATH]     dfpath: Path to readable data file
  --ocmd OCMD           OS command to send
  --ofpath [OFPATH]     ofpath: Path to readable os commands file
  --mcmd MCMD           Internal command to send


<ACTION:  'recv'>
usage: foxtrot.py recv [-h]

optional arguments:
  -h, --help  show this help message and exit


<ACTION:  'console'>
usage: foxtrot.py console [-h]

optional arguments:
  -h, --help  show this help message and exit


<ACTION:  'agent'>
usage: foxtrot.py agent [-h] --operation
                        {generate,delete,reset,ident,show,peek,post}
                        [--interval_low [INTERVAL_LOW]]
                        [--interval_high [INTERVAL_HIGH]]

optional arguments:
  -h, --help            show this help message and exit
  --operation {generate,delete,reset,ident,show,peek,post}
                        generate: generate agent record entry; delete: delete
                        agent record entry; reset: reset agent record entry to
                        defaults; show: show DNS record; peek: peek at job
                        data in the DNS record; post: post request for agent,
                        post response from the agent; ident: identify agent
                        record
  --interval_low [INTERVAL_LOW]
                        Check DNS record every (#)seconds (lower), set to 0 if
                        only once
  --interval_high [INTERVAL_HIGH]
                        Check DNS record every (#)seconds (high), set to 0 if
                        only once
```
### TODO: 
 - WebAPI for DNS updates
 - slave -> master safe content listing and fetch
 - tracking system of slaves at the master's side
 
 
Install packages:

`apt-get install pdns-server pdns-backend-sqlite3`


`pdns_server --launch=gpgsql --config`

`sqlite3 /var/lib/powerdns/pdns.sqlite3`

`rsync -avz root@138.68.234.147:/root/pdns pdns`
`pdnsutil  list-tsig-keys`
`pdnsutil generate-tsig-key test2 hmac-sha256`

## Powerdns
### Powerdns settings

Global `/etc/powerdns/pdns.conf`
SQL plugin `/etc/powerdns/pdns.d/pdns.local.gsqlite3.conf`


file: `powerdns.conf`
```conf
allow-dnsupdate-from=0.0.0.0/0
api=yes
api-key=************
dnsupdate=yes
include-dir=/etc/powerdns/pdns.d
launch=
security-poll-suffix=
setgid=pdns
setuid=pdns
### Optional
#webserver=yes
#webserver-address=0.0.0.0
#webserver-port=8081
```
## Nginx reverse proxy  
PDNS backchannel development - Work in progress
see file: `powerdns.nginx` 
query over HTTP:
`curl -v -k -X GET  -H 'X-API-Key: ********' https://138.68.234.147/api/v1/servers/localhost/zones/s3bucket.stream.`

`./pdns.py  add_zones --apikey "" --apihost 172.31.26.65  --apiport 8080 --zone "brtknd.pw" --zoneType NATIVE --content "ns1.brtknd.pw hostmaster.brtknd.pw 2017101501 10800 3600 604800 3600" --apiversion /api/v1 --disabled False`

`curl -v -X POST  -H 'X-API-Key: xxx' --data "@/home/admin/pdnsc/record.json" http://172.31.26.65:8080/api/v1/servers/localhost/zones`

`dig @138.68.234.147 +noall +answer s3bucket.stream any`


###  https://doc.powerdns.com/md/authoritative/dnsupdate/
select id from domains where name='s3bucket.stream';
1

insert into domainmetadata(domain_id, kind, content) values(1, 'ALLOW-DNSUPDATE-FROM','0.0.0.0/0');
insert into tsigkeys (name, algorithm, secret) values ('test', 'hmac-md5', 'kp4/24gyYsEzbuTVJRUMoqGFmN3LYgVDzJ/3oRSP7ys=');
insert into domainmetadata (domain_id, kind, content) values (1, 'TSIG-ALLOW-DNSUPDATE', 'test');

or:

`generate-tsig-key test hmac-md5`
