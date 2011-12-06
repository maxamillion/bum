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
# VERSION: 1.3
#==============================================================================

#=== FUNCTION ================================================================
# NAME: parser: repofile
# DESCRIPTION:  Parse a yum style .repo file
# PARAMETER 1:  some_file.repo
# RETURN VAL:   associative array -- ary[repo_name]=URL 
#=============================================================================
function parser:repofile {
    # handle return value
    unset __return__
    declare -A __return__

     
    

} # END FUNCTION: parser:repofile
