#!/bin/bash

if [ -z "$1" ]; then
	while read input; do
		curl -X POST -H 'Accept: application/json' \
    			--data-urlencode 'payload={"text":"'"$input"'"}' \
			https://hooks.slack.com/services/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 \
			> /dev/null
	done
else	
	DATA="$(cat "$1")"
	curl -X POST -H 'Accept: application/json' \
    		--data-urlencode 'payload={"text":"'"${DATA//\"/\\\"}"'"}' \
		https://hooks.slack.com/services/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 \
		> /dev/null
fi
