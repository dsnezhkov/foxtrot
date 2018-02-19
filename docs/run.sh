#!/bin/bash

AGENT="agent_195694e2"
TSIGNAME="test2"
TSIGRDATA="../config/tsig-test2.dat"
NSERVER="138.68.234.147"
DOMAIN="s3bucket.stream"
AGENTPATH="../foxtrot.py"

echo "============= Sending Data File=============="
echo "Master: Sending data file"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role master \
	--verbose info send --operation dfile --dfpath /tmp/datafile2

echo "Slave: Processing request"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role slave \
	--verbose info recv

echo "============= Sending OS Execution (file) =============="
echo "Master: Posting os exec() instructions"

echo "test" > /tmp/os.cmd2
echo ">>>"
cat /tmp/os.cmd2
echo "<<<"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role master \
	--verbose info send --operation ocmd --ofpath /tmp/os.cmd2

echo "Slave: Processing request"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role slave \
	--verbose info recv

echo "Master: Processing response"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role master \
	--verbose info recv

echo "============= Sending OS Execution (command line) =============="
echo "Master: Posting os exec() instructions"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role master  \
	--verbose info send --operation ocmd --ocmd 'ps -ef | grep bash'

echo "Slave: Showing raw record"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role slave \
	--verbose info agent --operation show

echo "Slave: Peeking at request"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role slave \
	--verbose info agent --operation peek

echo "Slave: Processing request"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role slave \
	--verbose info recv

echo "Master: Processing response"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role master \
	--verbose info recv

echo "Master: Peeking at response"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role slave \
	--verbose info agent --operation peek

echo "============= Misc =============="
echo "Master: Resetting agent's instructions"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role master \
	--verbose info agent --operation reset

echo "Slave: Resetting agent's instructions"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role master \
	--verbose info agent --operation reset

echo "Slave: Identifying myself"
echo ${AGENTPATH} --agent ${AGENT} --tsigname ${TSIGNAME} --tsigrdata ${TSIGRDATA} \
	--nserver ${NSERVER} --domain ${DOMAIN} --role master \
	--verbose info agent --operation ident
