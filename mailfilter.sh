#!/bin/bash

#postfix logs are piped into mailpipe, and filtered to anonymize emails before being saved to disk.

cat /home/margy/mailpipe | sed -u 's/to=<.*@.*\..*>/to=<anonymous@whoknows.where>/g' | 
	sed -u 's/from=<.*@.*\..*>/from=<anonymous@whoknows.where>/g' >> /home/margy/mail.log &
tail -f /home/margy/mail.log | tee >(grep --line-buffered -e warning -e error -e fatal -e panic | /home/margy/slack_message.sh) 
