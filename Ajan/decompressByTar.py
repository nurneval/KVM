
import tarfile

import sys
import os

workingPath = sys.argv[1]
fullFilePathToBeDecompressed = sys.argv[2]


def decompress(workingPath, compressedFileName ):

      print ("Decompressing :" + workingPath + compressedFileName )
      os.chdir(workingPath)
      tf = tarfile.open(compressedFileName)
      tf.extractall()
      print ("Decompressing finished successfully" )


if __name__ == '__main__':

    workingPath = sys.argv[1]
    fullFilePathToBeDecompressed = sys.argv[2]
    decompress(workingPath, fullFilePathToBeDecompressed)
