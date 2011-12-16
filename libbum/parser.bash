#==============================================================================
#
# FILE: parser.bash
#
# USAGE: source parser.bash
#
# DESCRIPTION: Anything that needs parsing in bum, it happens here.
#
# OPTIONS: NONE - This is to be a library file
# AUTHOR: Adam Miller - maxamillion@fedoraproject.org
#==============================================================================

#=== FUNCTION ================================================================
# NAME: fn_parse_repofile
# DESCRIPTION:  Parse a yum style .repo file
# PARAMETER 1:  some_file.repo
# RETURN VAL:   associative array -- ary[repo_name]=URL 
#=============================================================================
function fn_parse_repofile {
    # handle return value
    unset __return__
    declare -A __return__

    # Some simple checking of parameter passing
    if [[ -z "$1" ]]; then
        # Get path, otherwise return non-zero 
        rf_path="$1"
    else
        #FIXME  should probably come up with a defined way to handle stuff 
        #       like this ... maybe a bash RULE? ... meh, ponder ...  
        return 1
    fi


    ### Example repo entry (abbreviated where applicable to not linewrap):
    # [fedora]
    # name=Fedora $releasever - $basearch
    # failovermethod=priority
    # baseurl=http://download.fp.org/pub/f/l/r/$releasever/E/$basearch/os/
    # mirrorlist=https://m.fp.org/metalink?repo=f-$releasever&arch=$basearch
    # enabled=1
    # metadata_expire=7d
    # gpgcheck=1
    # gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$basearch

    #FIXME -- gracefully handle mirrorlists???? ... yeah ... later

    while read line 
    do
        # FIXME - better way to check for this?
        if [[ "${line:0:1}" == "[" ]]; then
            # This is the repositoryID ... snag it
            __return__["repoID"]="$line"
        else
            __return__["${line%%=*}"]="${line##=*}"
        fi
    done < $rf_path

} # END FUNCTION: fn_parse_repofile
