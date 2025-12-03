#!/bin/bash

<<<<<<< HEAD
# Initialize variables
InputFile=""
ConfigFile=""
WORKING_DIR_OPT="" # Variable to hold optional working directory from -w
TEMP_UNZIPPED="" # Track temporary unzipped file for cleanup

# Help function
Help()
{
   # Display Help
   echo
   echo "Syntax: startup [-i <JSON FILE>] [-c <CONFIG URL>] [-w <WORKDIR>] [-h]"
   echo "options:"
   echo "-h                Display this help"
   echo "-i <JSON FILE>    (Required) Path for input neo4j json file (supports .json or .json.gz)."
   echo "-c <CONFIG URL>   (Required) Url for conversion configuration file."
   echo "-w <WORKDIR>      (Optional) Working directory. Defaults to /mnt/repo."
   echo
   echo "Output will be written to: <WORKDIR>/nt/graph.nt.gz"
   echo
}

# Cleanup function to remove temporary files
cleanup() {
    if [ -n "$TEMP_UNZIPPED" ] && [ -f "$TEMP_UNZIPPED" ]; then
        echo "Cleaning up temporary file: $TEMP_UNZIPPED"
        rm -f "$TEMP_UNZIPPED"
    fi
}

# Set trap to ensure cleanup on exit
trap cleanup EXIT

# Get the options
while getopts ":hi:c:w:" option; do
   case $option in
      h) # display Help
         Help
         exit 0 # Use exit code 0 for help display
         ;;
      i) # Input file
         InputFile=$OPTARG;;
      c) # Config URL
         ConfigFile=$OPTARG;;
      w) # Optional Working Directory
         WORKING_DIR_OPT=$OPTARG;;
     \?) # Invalid option
         echo "Error: Invalid option -$OPTARG" >&2 # Redirect error to stderr
         Help
         exit 1;;
      :) # Missing argument for an option
         echo "Error: Option -$OPTARG requires an argument." >&2 # Redirect error to stderr
         Help
         exit 1;;
   esac
done

# --- Input Validation ---
if [ -z "$InputFile" ]; then
    echo "Error: Input file (-i) is required." >&2
    Help
    exit 1
fi

if [ -z "$ConfigFile" ]; then
    echo "Error: Config file URL (-c) is required." >&2
    Help
    exit 1
fi

# Check if input file exists
if [ ! -f "$InputFile" ]; then
    echo "Error: Input file '$InputFile' does not exist." >&2
    exit 1
fi

# --- Set Working Directory and Config File Path ---
# Use provided working dir, or environment variable, or default to /mnt/repo
WORKING_DIR=${WORKING_DIR_OPT:-${WORKING_DIR:-/mnt/repo}}

# Define output file path (uncompressed)
OutputFile="${WORKING_DIR}/nt/graph.nt"
# Define compressed output file path
OutputFileGz="${OutputFile}.gz"

# Create output directory if it doesn't exist
OUTPUT_DIR=$(dirname "$OutputFile")
if [ -n "$OUTPUT_DIR" ] && [ "$OUTPUT_DIR" != "." ]; then
    echo "Ensuring output directory exists: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
    if [ $? -ne 0 ]; then
        echo "Error: Could not create output directory '$OUTPUT_DIR'." >&2
        exit 1
    fi
fi

# Ensure the working directory exists (optional but good practice)
mkdir -p "$WORKING_DIR"
if [ $? -ne 0 ]; then
  echo "Error: Could not create working directory '$WORKING_DIR'." >&2
  exit 1
fi

# --- Handle gzipped input files ---
ACTUAL_INPUT_FILE="$InputFile"

if [[ "$InputFile" == *.json.gz ]]; then
    echo "Detected gzipped input file. Decompressing..."

    # Create temporary unzipped file in working directory
    TEMP_UNZIPPED="${WORKING_DIR}/$(basename "${InputFile%.gz}")"

    # Decompress the file
    gunzip -c "$InputFile" > "$TEMP_UNZIPPED"
    gunzip_exit_code=$?

    if [ $gunzip_exit_code -ne 0 ]; then
        echo "Error: Failed to decompress '$InputFile' with exit code $gunzip_exit_code." >&2
        exit 1
    fi

    echo "Decompressed to: $TEMP_UNZIPPED"
    ACTUAL_INPUT_FILE="$TEMP_UNZIPPED"
fi

# Define the local path for the downloaded config file
CONVERSION_MAPPING_FILE_NAME="${WORKING_DIR}/conversion-mapping.yaml"

echo "--- Configuration ---"
echo "Working Directory: $WORKING_DIR"
echo "Input File: $InputFile"
echo "Actual Input File: $ACTUAL_INPUT_FILE"
echo "Config URL: $ConfigFile"
echo "Output File: $OutputFile"
echo "Compressed Output: $OutputFileGz"
echo "Local Config Path: $CONVERSION_MAPPING_FILE_NAME"
echo "---------------------"

# --- Retrieve the conversion config file ---
echo "Downloading configuration from '$ConfigFile'..."
wget "$ConfigFile" -O "$CONVERSION_MAPPING_FILE_NAME"
wget_exit_code=$? # Capture exit code immediately

if [ $wget_exit_code -ne 0 ]; then
  echo "Error: wget of '$ConfigFile' failed with exit code $wget_exit_code. Exiting startup." >&2
  # Clean up potentially partially downloaded/empty file
  rm -f "$CONVERSION_MAPPING_FILE_NAME"
  exit 1
fi
echo "Configuration downloaded successfully."

# --- Run neo4j conversion ---
echo "Running conversion..."
python main.py -i "$ACTUAL_INPUT_FILE" -c "$CONVERSION_MAPPING_FILE_NAME" -o "$OutputFile"
python_exit_code=$? # Capture exit code

if [ $python_exit_code -ne 0 ]; then
  echo "Error: Python script main.py failed with exit code $python_exit_code." >&2
  exit 1
fi

echo "Conversion completed successfully."

# --- Compress the output file ---
echo "Compressing output file..."
# Remove existing .gz file if it exists
rm -f "$OutputFileGz"

# Compress the file
gzip -c "$OutputFile" > "$OutputFileGz"
gzip_exit_code=$?

if [ $gzip_exit_code -ne 0 ]; then
    echo "Error: Failed to compress output file with exit code $gzip_exit_code." >&2
    exit 1
fi

echo "Output compressed successfully to: $OutputFileGz"

# Get file size for logging
if command -v du &> /dev/null; then
    FILE_SIZE=$(du -h "$OutputFileGz" | cut -f1)
    echo "Compressed file size: $FILE_SIZE"
fi

echo "Startup script finished successfully."
exit 0