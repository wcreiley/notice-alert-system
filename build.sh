#!/bin/bash

function cmd_generateSampleDotEnvFile() {
    echo "Generating sample config dot.env file"
    cat .env  | sed -E "s/(.*=\")(.*)(\"[[:blank:]]*$)/\1<enter your data>\3/g" > config/dot.env
}

function availableActions() {
  local -r commands=$(cat build.sh | sed -E -n "s/(function[[:blank:]]*cmd_)(.*)(\(.*$)/\2/p" | xargs)
  echo "${commands}"
}

function main() {

    if [[ -z ${1} ]]; then
        echo "No action provided. Please provide an action."
        echo "Actions: $(availableActions)"
        exit 1
    fi

    local action="${1}"

    function_to_call="cmd_${action}"
    if ! type "${function_to_call}" &> /dev/null; then
        echo "Action '${action}' not found. Available actions: $(availableActions)"
        exit 1
    else
        echo "Executing action: '${action} ${@:2}'"
        "${function_to_call}" "${@:2}"
    fi
}

echo "Build Scripts"
main "$@"