#!/bin/bash

# e.g. filename.sh -s "2023-12-01 10:00:00" -o custom_output.txt "substring_to_search"
# e.g. filename.sh -s "30min ago" -o custom_output.txt "substring_to_search"

usage() {
    echo "Usage: $0 [-s <start_time>] [-o <output_file>] <substring>"
    echo "  -s <start_time>   Optional: Start time for filtering logs (e.g., '2023-12-01 10:00:00' or '30 min ago')."
    echo "  -o <output_file>  Optional: Output file to write logs. Default is 'filtered_logs.txt'."
    echo "  <substring>       Substring to search for in journalctl logs."
    exit 1
}

# Default values
OUTPUT_FILE="filtered_logs.txt"
START_TIME=""

# Parse options
while getopts "s:o:" opt; do
    case $opt in
        s) START_TIME="$OPTARG" ;;
        o) OUTPUT_FILE="$OPTARG" ;;
        *) usage ;;
    esac
done

# The substring to search for in the logs should be the remaining argument
shift $((OPTIND-1))
if [ $# -lt 1 ]; then
    usage
fi
SUBSTRING="$1"

CMD="journalctl --no-pager"
if [ -n "$START_TIME" ]; then
    CMD="$CMD --since=\"$START_TIME\""
fi
CMD="$CMD | grep \"$SUBSTRING\" > \"$OUTPUT_FILE\""

echo "Running command: '$CMD'"
eval "$CMD"
echo "Logs filtered and saved to $OUTPUT_FILE."
