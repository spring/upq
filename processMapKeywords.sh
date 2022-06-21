#!/bin/bash

# get map keywords from the springrts.com wiki and update springfiles db
# TODO probably safer to replace this with web form + role that allows only some users to change the keywords

LOG_FILE="/home/springfiles/processMapKeywords.log"
ALT_LOG_FILE="/home/springfiles/processMapKeywords.log.1"
MAX_LOG_SIZE_B=100000000		# 100 mb

log () {
	echo "$(date "+%F %T") : $1" >> "$LOG_FILE" 
}


# simple rotation of log file
if [ -f "$LOG_FILE" ] && [ "$(stat -c '%s' $LOG_FILE)" -gt "$MAX_LOG_SIZE_B" ]; then 
	if [ -f "$ALT_LOG_FILE" ]; then
		rm "$ALT_LOG_FILE"
	fi
	mv "$LOG_FILE" "$ALT_LOG_FILE"
fi

log "------------- PROCESSING MAP KEYWORDS FROM WIKI"

# safe?
linesToProcess=$(wget -qO- "https://springrts.com/wiki/MapKeywords" | awk '/---START---/,/---END---/' | grep -v '\-\-\-')

if [ -z "$linesToProcess" ]; then
	log "no lines to process, aborting..."
else
	lines=$(echo "$linesToProcess" | wc -l)
	log "$lines lines found"
fi

while read line; do
	log "processing $line"
	mapName=${line%%;*}
	mapName=${mapName//[^a-zA-Z0-9_ \-]/}	# sanitize
	keywordsStr=${line#*;}
	keywordsStr=${keywordsStr//[^a-z0-9;]/} # sanitize

	IFS=';' read -r -a keywords <<< "$keywordsStr"
	# delete existing keyword records for this map's files
	mysql -u springfiles springfiles -e "DELETE fk FROM file_keyword fk LEFT JOIN file f ON (f.fid=fk.fid) WHERE f.name_without_version='$mapName'"
	# add recird for each file and keyword
	fids=$(mysql -u springfiles springfiles -N -r -e "SELECT fid FROM file WHERE name_without_version='$mapName'")
	fids=($fids)
	for fid in "${fids[@]}"
	do
		for keyword in "${keywords[@]}"
		do
			mysql -u springfiles springfiles -e "INSERT INTO file_keyword(fid,keyword) VALUES($fid,'$keyword')"
		done
	done

done <<< $linesToProcess


