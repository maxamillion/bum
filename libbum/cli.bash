#=============================================================================
#
# FILE: cli.bash
#
# USAGE: sourced by bum
#
# DESCRIPTION: Command-line parsing and dispatch for bum.
#=============================================================================

#=== FUNCTION ================================================================
# NAME: fn_usage
# DESCRIPTION: Display command usage.
# PARAMETER 1: program name
#=============================================================================
function fn_usage {
    printf 'Usage: %s [--help] [--version] COMMAND [ARGUMENTS...]\n' "$1"
    printf '\nCommands:\n'
    printf '  install PACKAGE...  Install packages (not implemented)\n'
    printf '  upgrade [PACKAGE...] Upgrade packages (not implemented)\n'
    printf '  remove PACKAGE...   Remove packages (not implemented)\n'
}

#=== FUNCTION ================================================================
# NAME: fn_main
# DESCRIPTION: Validate and dispatch command-line arguments.
# PARAMETER 1+: command-line arguments
#=============================================================================
function fn_main {
    local program=${0##*/}
    local command

    if (( $# == 0 )); then
        fn_usage "$program" >&2
        return 2
    fi

    case "$1" in
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

    case "$command" in
        install|upgrade|remove)
            if [[ "$command" != upgrade && $# -eq 0 ]]; then
                printf '%s: command %s requires a package argument\n' \
                    "$program" "$command" >&2
                return 2
            fi
            printf '%s: %s is not implemented yet\n' "$program" \
                "$command" >&2
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
