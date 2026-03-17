#!/usr/bin/env bash

extract_strict_merge_recommendation() {
  local review_file="$1"
  local -a matches=()
  local -a unique_matches=()
  local line

  while IFS= read -r line; do
    case "$line" in
      "MERGE RECOMMENDATION: approve")
        matches+=("approve")
        ;;
      "MERGE RECOMMENDATION: reject")
        matches+=("reject")
        ;;
    esac
  done < "$review_file"

  if (( ${#matches[@]} == 0 )); then
    return 1
  fi

  while IFS= read -r line; do
    [[ -n "$line" ]] && unique_matches+=("$line")
  done < <(printf '%s\n' "${matches[@]}" | LC_ALL=C sort -u)

  if (( ${#unique_matches[@]} != 1 )); then
    return 1
  fi

  printf '%s\n' "${unique_matches[0]}"
}
