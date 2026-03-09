#!/bin/bash

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
   echo "-i <JSON FILE>    (Required) Path for input neo4j json file (supports .json, .json.gz, or .json.zst)."
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
         exit 0
         ;;
      i) # Input file
         InputFile=$OPTARG;;
      c) # Config URL
         ConfigFile=$OPTARG;;
      w) # Optional Working Directory
         WORKING_DIR_OPT=$OPTARG;;
     \?) # Invalid option
         echo "Error: Invalid option -$OPTARG" >&2
         Help
         exit 1;;
      :) # Missing argument for an option
         echo "Error: Option -$OPTARG requires an argument." >&2
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
WORKING_DIR=${WORKING_DIR_OPT:-${WORKING_DIR:-/mnt/repo}}
OutputFile="${WORKING_DIR}/nt/graph.nt"
OutputFileGz="${OutputFile}.gz"

# Create output directory
OUTPUT_DIR=$(dirname "$OutputFile")
mkdir -p "$OUTPUT_DIR"
mkdir -p "$WORKING_DIR"

# --- Handle compressed input files (Gzip or Zstd) ---
ACTUAL_INPUT_FILE="$InputFile"

if [[ "$InputFile" == *.gz ]]; then
    echo "Detected gzipped input file. Decompressing..."
    TEMP_UNZIPPED="${WORKING_DIR}/$(basename "${InputFile%.gz}")"
    gunzip -c "$InputFile" > "$TEMP_UNZIPPED"
    DECOMPRESS_STATUS=$?
elif [[ "$InputFile" == *.zst ]]; then
    echo "Detected zstd compressed input file. Decompressing..."
    if ! command -v zstd &> /dev/null; then
        echo "Error: zstd is not installed. Please install it to process .zst files." >&2
        exit 1
    fi
    TEMP_UNZIPPED="${WORKING_DIR}/$(basename "${InputFile%.zst}")"
    zstd --memory=2048MB -d -c "$InputFile" > "$TEMP_UNZIPPED"
    DECOMPRESS_STATUS=$?
fi

# Check if decompression was successful (if it was triggered)
if [ -n "$TEMP_UNZIPPED" ]; then
    if [ $DECOMPRESS_STATUS -ne 0 ]; then
        echo "Error: Failed to decompress '$InputFile'." >&2
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
echo "---------------------"

# --- Retrieve the conversion config file ---
echo "Downloading configuration from '$ConfigFile'..."
wget "$ConfigFile" -O "$CONVERSION_MAPPING_FILE_NAME"
if [ $? -ne 0 ]; then
  echo "Error: wget of '$ConfigFile' failed." >&2
  rm -f "$CONVERSION_MAPPING_FILE_NAME"
  exit 1
fi

# --- Run neo4j conversion ---
echo "Running conversion..."
python main.py -i "$ACTUAL_INPUT_FILE" -c "$CONVERSION_MAPPING_FILE_NAME" -o "$OutputFile"
if [ $? -ne 0 ]; then
  echo "Error: Python script main.py failed." >&2
  exit 1
fi

# --- Compress the output file ---
echo "Compressing output file to Gzip..."
rm -f "$OutputFileGz"
gzip -c "$OutputFile" > "$OutputFileGz"

if [ $? -eq 0 ]; then
    echo "Output compressed successfully to: $OutputFileGz"
    [ -f "$OutputFile" ] && rm "$OutputFile" # Clean up uncompressed output
else
    echo "Error: Failed to compress output file." >&2
    exit 1
fi

echo "Startup script finished successfully."
exit 0