#=============================================================================
#
# FILE: parser.bash
#
# USAGE: sourced by bum
#
# DESCRIPTION: Parse the supported subset of yum-style repository files.
#=============================================================================

#=== FUNCTION ================================================================
# NAME: fn_parse_repofile
# DESCRIPTION: Parse sections and key/value pairs from a .repo file.
# PARAMETER 1: readable repository configuration path
# RETURN VAL: __return__["section|key"] values and __return__["error"]
#=============================================================================
function fn_parse_repofile {
    unset __return__
    declare -gA __return__=()

    local file=${1-}
    local line section key value
    local line_number=0

    if [[ -z "$file" ]]; then
        __return__[error]='repository file path is required'
        return 2
    fi
    if [[ ! -f "$file" || ! -r "$file" ]]; then
        __return__[error]="not a readable regular file: $file"
        return 2
    fi

    section=''
    while IFS= read -r line || [[ -n "$line" ]]; do
        ((line_number += 1))
        line=${line%$'\r'}
        line="${line#"${line%%[!$' \t']*}"}"
        line="${line%"${line##*[!$' \t']}"}"

        [[ -z "$line" || "$line" == \#* || "$line" == \;* ]] && continue

        if [[ "$line" == \[*\] ]]; then
            section=${line#\[}
            section=${section%\]}
            if [[ -z "$section" || "$section" == *'['* || \
                "$section" == *']'* ]]; then
                __return__[error]="$file:$line_number: invalid section"
                return 2
            fi
            __return__["$section|__section__"]="$section"
            continue
        fi

        if [[ -z "$section" || "$line" != *=* ]]; then
            __return__[error]="$file:$line_number: expected section or key=value"
            return 2
        fi

        key=${line%%=*}
        value=${line#*=}
        key="${key#"${key%%[!$' \t']*}"}"
        key="${key%"${key##*[!$' \t']}"}"
        value="${value#"${value%%[!$' \t']*}"}"
        value="${value%"${value##*[!$' \t']}"}"

        if [[ -z "$key" || "$key" == *[$' \t']* ]]; then
            __return__[error]="$file:$line_number: invalid key"
            return 2
        fi
        __return__["$section|$key"]=$value
    done < "$file"

    if (( ${#__return__[@]} == 0 )); then
        __return__[error]="no repository sections found: $file"
        return 2
    fi
    return 0
}
