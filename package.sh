#!/bin/bash

AUTHOR="thierry.tra@hotmail.com"
TITLE="Telegram notification plugin"
PKG_NAME="telegram_notify"
DESCRIPTION="Send monitoring notifications to a configurable Telegram bot. Have a look at the readme in the git repository for further instructions."
PLUGIN_VERSION="2.0.0"
CHECKMK_MIN_VERSION="2.4.0"
CHECKMK_PKG_VERSION=$CHECKMK_MIN_VERSION
DOWNLOAD_URL="https://bitbucket.org/Nerothank/checkmk_notify_telegram"

SOURCE_PATH=$(pwd)
OUTPUT_PATH=$(pwd)

# suppress macOS extended attributes in tar archives
export COPYFILE_DISABLE=1

# remove any python compiled binaries
find . -name "*.pyc" -delete

# STOP EDITING HERE
current_dir=$(pwd)
cd "$SOURCE_PATH"

filedict=""
numfiles=0

# collect all files in all directories and tar them separately
while read dir; do
    cd "$dir"

    dir_files="$(find -L -type f)"
    pretty_key=$(echo "$dir" | sed -E 's/\.\///g')

    ## tar files
    tar --dereference -cf "$OUTPUT_PATH/$dir.tar" *
    cd - &>/dev/null

    ## start list -> 'key': [
    filedict="$filedict'$pretty_key': ["

    ## add entries -> 'entry',
    first=1
    for file in $dir_files; do
        pretty_file=$(echo "$file" | sed -E 's/^\.\///g')
        if [ $first -eq 1 ]; then
            filedict="$filedict'$pretty_file'"
            first=0
        else
            filedict="$filedict,'$pretty_file'"
        fi
        numfiles=$(( numfiles + 1 ))
    done

    ## close list -> ],
    filedict="$filedict],"
done < <(find . -maxdepth 1 -type d -name "[!.]*")

## remove trailing comma
filedict="${filedict%,}"

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

cd "$current_dir"
