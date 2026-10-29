#=============================================================================
# Command-line parsing and dispatch for bum.
#=============================================================================

function fn_usage {
    printf 'Usage: %s [--help] [--version] COMMAND [ARGUMENTS...]\n' "$1"
    printf '\nCommands:\n'
    printf '  plan install PACKAGE --repo REPO_ID [--repo-dir DIR]\n'
    printf '       [--cache-dir DIR] [--download-dir DIR]\n'
    printf '  plan remove PACKAGE [--arch ARCH]\n'
    printf '  install PACKAGE...  Install packages (not implemented)\n'
    printf '  upgrade [PACKAGE...] Upgrade packages (not implemented)\n'
    printf '  remove PACKAGE...   Remove packages (not implemented)\n'
}

function fn_plan_install {
    local program=${0##*/} package='' repo_id='' repo_dir cache_dir
    local python helper url option value
    local download_dir=''
    local have_repo_dir=0 have_cache_dir=0 have_download_dir=0

    repo_dir=${BUM_REPODIR:-${glbl_yum_repo_dir:-/etc/yum.repos.d}}
    if (( $# < 1 )); then
        printf '%s: plan install requires a package\n' "$program" >&2
        return 2
    fi
    package=$1
    if [[ -z $package || $package == -* || $package =~ [[:space:][:cntrl:]] ]]; then
        printf '%s: invalid package name\n' "$program" >&2
        return 2
    fi
    shift

    while (( $# )); do
        option=$1
        case $option in
            --repo|--repo-dir|--cache-dir|--download-dir)
                if (( $# < 2 )) || [[ -z $2 || $2 == --* ]]; then
                    printf '%s: option %s requires a value\n' \
                        "$program" "$option" >&2
                    return 2
                fi
                value=$2
                case $option in
                    --repo)
                        if [[ -n $repo_id ]]; then
                            printf '%s: duplicate --repo\n' "$program" >&2
                            return 2
                        fi
                        repo_id=$value
                        ;;
                    --repo-dir)
                        if (( have_repo_dir )); then
                            printf '%s: duplicate --repo-dir\n' \
                                "$program" >&2
                            return 2
                        fi
                        repo_dir=$value
                        have_repo_dir=1
                        ;;
                    --cache-dir)
                        if (( have_cache_dir )); then
                            printf '%s: duplicate --cache-dir\n' \
                                "$program" >&2
                            return 2
                        fi
                        cache_dir=$value
                        have_cache_dir=1
                        ;;
                    --download-dir)
                        if (( have_download_dir )); then
                            printf '%s: duplicate --download-dir\n' \
                                "$program" >&2
                            return 2
                        fi
                        download_dir=$value
                        have_download_dir=1
                        ;;
                esac
                shift 2
                ;;
            *)
                printf '%s: unexpected argument: %s\n' \
                    "$program" "$option" >&2
                return 2
                ;;
        esac
    done

    if [[ -z $repo_id ]]; then
        printf '%s: plan install requires --repo REPO_ID\n' \
            "$program" >&2
        return 2
    fi
    if (( ! have_cache_dir )); then
        cache_dir=${BUM_CACHEDIR:-${XDG_CACHE_HOME:-${HOME:-/}}/bum}
    fi

    # Validate the repository before touching the cache path.
    if ! fn_load_repositories "$repo_dir"; then
        printf '%s: %s\n' "$program" "${__return__[error]}" >&2
        return 2
    fi
    if [[ -z ${__return__["$repo_id|__section__"]+yes} ]]; then
        printf '%s: unknown repository: %s\n' "$program" "$repo_id" >&2
        return 2
    fi
    if [[ ${__return__["$repo_id|enabled"]-1} != 1 ]]; then
        printf '%s: repository is disabled: %s\n' "$program" "$repo_id" >&2
        return 2
    fi
    url=${__return__["$repo_id|baseurl"]}

    local current_uid
    current_uid=$(id -u)
    if (( have_download_dir )); then
        if [[ ! -e $download_dir && ! -L $download_dir ]]; then
            (umask 077; mkdir -p -- "$download_dir") || {
                printf '%s: cannot create download cache: %s\n' \
                    "$program" "$download_dir" >&2
                return 2
            }
        fi
        local download_uid download_mode
        download_uid=$(stat -c %u -- "$download_dir" 2>/dev/null) || \
            download_uid=''
        download_mode=$(stat -c %a -- "$download_dir" 2>/dev/null) || \
            download_mode=''
        if [[ -L $download_dir || ! -d $download_dir || \
            ! -w $download_dir || $download_uid != "$current_uid" || \
            -z $download_mode ]] || (( (8#$download_mode & 077) != 0 )); then
            printf '%s: download path must be a private writable directory: %s\n' \
                "$program" "$download_dir" >&2
            return 2
        fi
    fi

    if [[ ! -e $cache_dir && ! -L $cache_dir ]]; then
        (umask 077; mkdir -p -- "$cache_dir") || {
            printf '%s: cannot create cache directory: %s\n' \
                "$program" "$cache_dir" >&2
            return 2
        }
    fi
    local cache_uid cache_mode
    cache_uid=$(stat -c %u -- "$cache_dir" 2>/dev/null) || cache_uid=''
    cache_mode=$(stat -c %a -- "$cache_dir" 2>/dev/null) || cache_mode=''
    if [[ -L $cache_dir || ! -d $cache_dir || ! -w $cache_dir ||
          $cache_uid != "$current_uid" || -z $cache_mode ]] ||
       (( (8#$cache_mode & 077) != 0 )); then
        printf '%s: cache path must be a writable directory: %s\n' \
            "$program" "$cache_dir" >&2
        return 2
    fi

    helper=${BUM_REPOMD_HELPER:-$(
        cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd
    )/helpers/bum-repomd.py}
    python=${BUM_PYTHON:-python3}
    if ! command -v "$python" >/dev/null 2>&1; then
        printf '%s: Python interpreter not found: %s\n' "$program" "$python" >&2
        return 2
    fi
    if ! "$python" -c 'import librepo, solv' >/dev/null 2>&1; then
        printf '%s: planning dependencies missing\n' "$program" >&2
        printf '%s\n' 'Python modules librepo and solv are required' >&2
        return 2
    fi
    local -a helper_args=("$helper" "$url" "$package" --cache-dir "$cache_dir")
    if (( have_download_dir )); then
        helper_args+=(--download "$download_dir")
    fi
    "$python" "${helper_args[@]}"
}

function fn_plan_remove {
    local program=${0##*/} package=${1-} arch=${BUM_ARCH:-x86_64}
    local python helper inventory_helper solver_helper
    if [[ -z $package || $package == -* || $package =~ [^a-zA-Z0-9._+:-] ||
          -z $arch || $arch =~ [^a-zA-Z0-9_+-] ]]; then
        printf '%s: plan remove requires a valid package name\n' \
            "$program" >&2
        return 2
    fi
    shift
    if (( $# )); then
        if (( $# != 2 )) || [[ $1 != --arch || -z $2 || $2 == -* ]]; then
            printf '%s: expected optional --arch ARCH\n' "$program" >&2
            return 2
        fi
        arch=$2
    fi
    if [[ -z $arch || $arch =~ [^a-zA-Z0-9_+-] ]]; then
        printf '%s: invalid architecture: %s\n' "$program" "$arch" >&2
        return 2
    fi
    python=${BUM_PYTHON:-python3}
    if ! command -v "$python" >/dev/null 2>&1; then
        printf '%s: Python interpreter not found: %s\n' "$program" "$python" >&2
        return 2
    fi
    if ! "$python" -c 'import solv' >/dev/null 2>&1; then
        printf '%s: planning dependency missing: Python module solv\n' \
            "$program" >&2
        return 2
    fi
    helper_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
    inventory_helper=${BUM_INVENTORY_HELPER:-$helper_root/helpers/bum-rpm-inventory.py}
    solver_helper=${BUM_SOLVER_HELPER:-$helper_root/helpers/bum-solver.py}
    helper=${BUM_PLAN_REMOVE_HELPER:-$helper_root/helpers/bum-plan-remove.py}
    printf '{"protocol":1,"package":"%s","arch":"%s"}' \
        "$package" "$arch" |
        "$python" "$helper" --inventory "$inventory_helper" \
            --solver "$solver_helper"
}

function fn_main {
    local program=${0##*/} command

    if (( $# == 0 )); then
        fn_usage "$program" >&2
        return 2
    fi
    case $1 in
        --help|-h)
            fn_usage "$program"
            return 0
            ;;
        --version|-V)
            printf '%s %s\n' "$program" "${glbl_version:-unknown}"
            return 0
            ;;
        --)
            shift
            ;;
    esac
    if (( $# == 0 )); then
        fn_usage "$program" >&2
        return 2
    fi

    command=$1
    shift
    case $command in
        plan)
            if (( $# == 0 )); then
                printf '%s: plan requires install or remove\n' \
                    "$program" >&2
                return 2
            fi
            case $1 in
                install)
                    shift
                    fn_plan_install "$@"
                    ;;
                remove)
                    shift
                    fn_plan_remove "$@"
                    ;;
                *)
                    printf '%s: supported plans are: install, remove\n' \
                        "$program" >&2
                    return 2
                    ;;
            esac
            ;;
        install|upgrade|remove)
            if [[ $command != upgrade && $# -eq 0 ]]; then
                printf '%s: command %s requires a package argument\n' \
                    "$program" "$command" >&2
                return 2
            fi
            printf '%s: %s is not implemented yet\n' \
                "$program" "$command" >&2
            return 3
            ;;
        --help|-h)
            fn_usage "$program"
            return 0
            ;;
        --version|-V)
            printf '%s %s\n' "$program" "${glbl_version:-unknown}"
            return 0
            ;;
        -* )
            printf '%s: unknown option: %s\n' "$program" "$command" >&2
            fn_usage "$program" >&2
            return 2
            ;;
        *)
            printf '%s: unknown command: %s\n' "$program" "$command" >&2
            fn_usage "$program" >&2
            return 2
            ;;
    esac
}
