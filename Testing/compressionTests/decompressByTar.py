
import tarfile

import sys
import os

workingPath = sys.argv[1]
fullFilePathToBeDecompressed = sys.argv[2]


def decompress(workingPath, compressedFileName ):

      print ("Decompressing :" + workingPath + compressedFileName + " to " + decompressionPath )
      os.chdir(workingPath)
      decompressionPath = workingPath+ "/decomplar"
      tf = tarfile.open(compressedFileName)
      tf.extractall(decompressionPath)
      print ("Decompressing finished successfully" )


if __name__ == '__main__':

    workingPath = sys.argv[1]
    fullFilePathToBeDecompressed = sys.argv[2]
    decompress(workingPath, fullFilePathToBeDecompressed)
