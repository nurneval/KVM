
import tarfile

import sys
import os




def compress(workingPath,fileNameToBeCompressed, compressedFileName, compressionMode ):
    print ("creating archive: " + workingPath + compressedFileName )

    os.chdir(workingPath)
    out = tarfile.open(compressedFileName, mode=compressionMode)
    try:
	    print ("adding " + fileNameToBeCompressed)
	    out.add(fileNameToBeCompressed)
    finally:
        print ("closing" + compressedFileName)
        out.close()


    return;
