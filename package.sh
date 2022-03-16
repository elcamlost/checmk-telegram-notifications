#!/bin/bash

AUTHOR="thierry.tra@hotmail.com"
TITLE="Telegram notification plugin"
PKG_NAME="telegram_notify"
DESCRIPTION="Send monitoring notifications to a configurable Telegram bot. Have a look at the readme in the git repository for further instructions."
PLUGIN_VERSION="1.4.2"
CHECKMK_MIN_VERSION="2.0.0"
CHECKMK_PKG_VERSION=$CHECKMK_MIN_VERSION
DOWNLOAD_URL="https://bitbucket.org/Nerothank/checkmk_notify_telegram"

SOURCE_PATH=$(pwd)
OUTPUT_PATH=$(pwd)

# remove any python compiled binaries
find . -name "*.pyc" -delete

# STOP EDITING HERE
current_dir=$(pwd)
cd "$SOURCE_PATH"

declare -A files

# collect all files in all directories and tar them separately
while read dir; do
    cd "$dir"

    ## update file dictionary
    files[$dir]="$(find -L -type f)"

    ## tar files
    tar --dereference -cf "$OUTPUT_PATH/$dir.tar" *
    cd - &>/dev/null
done < <(find . -maxdepth 1 -type d -name "[!.]*")

# construct the info dictionary/JSON
filedict=""
numfiles=0
## output file list for every dir
for key in "${!files[@]}"; do
    pretty_key=$(echo $key | sed -E 's/\.\///g')

    ## start list -> 'key: [
    filedict="$filedict'$pretty_key': ["

    ## add entries -> 'entry',
    for file in ${files[$key]}; do
        pretty_file=$(echo $file | sed -E 's/^\.\///g')
        filedict="$filedict'$pretty_file',"
        numfiles=$(( $numfiles + 1 ))
    done

    ## remove trailing comma
    filedict="${filedict::-1}"

    ## close list -> ],
    filedict="$filedict],"
done

## remove trailing comma
filedict="${filedict::-1}"

# finalize info dict/JSON
info="{'author': '$AUTHOR',
 'description': '$DESCRIPTION',
 'download_url': '$DOWNLOAD_URL',
 'files': {$filedict},
 'name': '$PKG_NAME',
 'num_files': $numfiles,
 'title': '$TITLE',
 'version': '$PLUGIN_VERSION',
 'version.min_required': '$CHECKMK_MIN_VERSION',
 'version.packaged': '$CHECKMK_PKG_VERSION'}"

cd "$OUTPUT_PATH"

echo $info > info
echo $info | sed -E "s/'/"'"'"/g" > info.json

tar -c *.tar info info.json | gzip --best - > "$OUTPUT_PATH/$PKG_NAME.mkp"

# cleanup temp files
rm -f *.tar info info.json

cd $current_dir
