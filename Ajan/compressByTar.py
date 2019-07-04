
import tarfile

import sys




def compress(fullFilePathToBeCompressed,fullFilePathOfCompressedFile, compressionMode  ):
    print ("creating archive:" + fullFilePathOfCompressedFile)


    out = tarfile.open(fullFilePathOfCompressedFile, mode=compressionMode)
    try:
	    print ("adding " + fullFilePathToBeCompressed)
	    out.add(fullFilePathToBeCompressed)
    finally:
        print ("closing" + fullFilePathOfCompressedFile)
        out.close()


    return;
