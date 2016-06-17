#!/usr/bin/env python3

import sys
import os
from subprocess import run
from shutil import rmtree

"""Zip up each directory in the current folder as separate archives to a specified location (default hardcoded).
  The original directories will be deleted."""

_ZIP_OUTPUT_DIR = r"c:\Test\ZippedOutput"

def main(zip_folder):
   if not (os.path.exists(zip_folder)):
       print("Error: Output folder '{0}' does not exist.")
       return
 
   dirs = [d for d in os.listdir(".") if os.path.isdir(d)]

   for d in dirs:
       print(d)
       archiveName = os.path.join(zip_folder,"%s.zip" % d)
       
       if os.path.exists(archiveName):
           print("Error: Archive %s already exists. Skipping." % d)
           continue
       
       zipCommand = r'7z a "{0}" ".\{1}\*" -sdel'.format(archiveName, d)
       result = run(zipCommand)
       
       if result.returncode == 0 and os.path.exists(archiveName):
           rmtree(d, ignore_errors=True)

if __name__ == "__main__":
    _zip_folder = _ZIP_OUTPUT_DIR
    if len(sys.argv) > 1:
      _zip_folder = sys.argv[1]
      
    main(_zip_folder)



