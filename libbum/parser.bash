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

#=== FUNCTION ================================================================
# NAME: fn_load_repositories
# DESCRIPTION: Discover and validate supported repository definitions.
# PARAMETER 1: directory containing *.repo files
# RETURN VAL: __return__[repo|key] values
#=============================================================================
function fn_load_repositories {
    unset __return__
    declare -gA __return__=()

    local directory=${1-}
    local file repo key value parsed_key
    local -a files=()
    local -A parsed=() seen_repos=() repositories=() file_sections=()
    local -A settings=() results=()
    local had_nullglob=0

    if [[ -z "$directory" || ! -d "$directory" || ! -r "$directory" ]]; then
        __return__[error]="not a readable repository directory: $directory"
        return 2
    fi

    shopt -q nullglob && had_nullglob=1
    shopt -s nullglob
    files=("$directory"/*.repo)
    (( had_nullglob == 1 )) || shopt -u nullglob
    if (( ${#files[@]} == 0 )); then
        __return__[error]="no .repo files found in: $directory"
        return 2
    fi

    for file in "${files[@]}"; do
        file_sections=()
        settings=()
        if ! fn_parse_repofile "$file"; then
            __return__[error]=${__return__[error]}
            return 2
        fi
        parsed=()
        for parsed_key in "${!__return__[@]}"; do
            parsed["$parsed_key"]=${__return__[$parsed_key]}
            if [[ "$parsed_key" == *__section__ ]]; then
                file_sections[${__return__[$parsed_key]}]=1
            fi
        done
        for parsed_key in "${!parsed[@]}"; do
            [[ "$parsed_key" == *__section__ ]] || continue
            repo=${parsed[$parsed_key]}
            if [[ -n ${seen_repos[$repo]+present} ]]; then
                __return__[error]="duplicate repository id: $repo"
                return 2
            fi
            seen_repos[$repo]=1
            repositories[$repo]=1
        done
        for parsed_key in "${!parsed[@]}"; do
            [[ "$parsed_key" == *__section__ ]] && continue
            repo=${parsed_key%%|*}
            key=${parsed_key#*|}
            value=${parsed[$parsed_key]}
            case "$key" in
                name|baseurl|enabled|gpgcheck|gpgkey) ;;
                *)
                    __return__[error]="$file: unsupported option '$key' in [$repo]"
                    return 2
                    ;;
            esac
            case "$key" in
                enabled|gpgcheck)
                    if [[ "$value" != 0 && "$value" != 1 && \
                        "$value" != true && "$value" != false && \
                        "$value" != yes && "$value" != no ]]; then
                        __return__[error]="$file: invalid $key value in [$repo]"
                        return 2
                    fi
                    case "$value" in
                        1|true|yes) value=1 ;;
                        0|false|no) value=0 ;;
                    esac
                    ;;
                baseurl)
                    if [[ -z "$value" ]]; then
                        __return__[error]="$file: empty baseurl in [$repo]"
                        return 2
                    fi
                    ;;
            esac
            settings["$repo|$key"]=$value
        done
        for parsed_key in "${!settings[@]}"; do
            results["$parsed_key"]=${settings[$parsed_key]}
        done
        for repo in "${!file_sections[@]}"; do
            if [[ -z ${__return__["$repo|enabled"]+present} ]]; then
                results["$repo|enabled"]=1
            fi
            if [[ -z ${__return__["$repo|gpgcheck"]+present} ]]; then
                results["$repo|gpgcheck"]=1
            fi
        done
    done
    for repo in "${!repositories[@]}"; do
        if [[ ${results["$repo|enabled"]-1} == 1 && \
            -z ${results["$repo|baseurl"]-} ]]; then
            __return__[error]="repository [$repo] has no baseurl"
            return 2
        fi
    done
    for parsed_key in "${!results[@]}"; do
        __return__["$parsed_key"]=${results[$parsed_key]}
    done
    return 0
}
