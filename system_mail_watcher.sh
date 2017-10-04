#!/bin/bash

while true; do
	if [ -s /var/mail/margy ]; then
		/home/margy/slack_message.sh /var/mail/margy
		cat /var/mail/margy >> /home/margy/mbox
		> /var/mail/margy
	fi
	sleep 300
done
