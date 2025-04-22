#!/bin/bash

# Help                                                     #
############################################################
Help()
{
   # Display Help
   echo
   echo "Syntax: startup [-i|-c|-o|-h]"
   echo "options:"
   echo "-h                Display this help"
   echo "-i <JSON FILE>    Path for input neo4j json file."
   echo "-c <CONFIG FILE>  Url for conversion configuration file."
   echo "-o <OUTPUT FILE>  Path for .ht output file"
   echo
}

# Get the options
while getopts ":h:i:c:o:" option; do
   case $option in
      h) # display Help
         Help
         exit;;
      i) # Enter a name
         InputFile=$OPTARG;;
      c) # Enter a name
         ConfigFile=$OPTARG;;
      o) # Enter a name
         OutputFile=$OPTARG;;
     \?) # Invalid option
         echo "Error: Invalid option"
         exit;;
   esac
done

# retrieve the conversion config file
wget $ConfigFile
if [ $? -ne 0 ]; then
  echo "wget of $ConfigFile failed with exit code $?. Exiting startup"
  exit 1
fi

# run neo4j conversion
python main.py -i $InputFile -c $ConfigFile -o $OutputFile
