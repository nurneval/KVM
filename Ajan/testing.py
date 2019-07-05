
import sys
import datetime
import os


import compressByTar
import decompressByTar
import memoryUsage


compressedFileName= ''
fullFilePathOfCompressedFile= ''

workingPath= sys.argv[1]
fileNameToBeCompressed= sys.argv[2]

class State:

  def __init__(self, workingPath, fileNameToBeCompressed):
    self.currentTime = datetime.datetime.now()
    self.fileSize = os.path.getsize(workingPath+fileNameToBeCompressed)
    self.memoryUsageInfo = memoryUsage.using()


def prepareParameters(compressionModeName):

    global fullFilePathToBeCompressed
    global compressedFileName
    global fullFilePathOfCompressedFile

    fullFilePathToBeCompressed= workingPath +   fileNameToBeCompressed
    compressedFileName= fileNameToBeCompressed + '_' + compressionModeName + '.tar'
    fullFilePathOfCompressedFile= workingPath   + compressedFileName




def printStatistics(state1=State ,  state2=State, state3= State):
  totalTimeForCompression= state2.currentTime - state1.currentTime
  totalTimeForDecompression= state3.currentTime - state2.currentTime
  compressionRatio= state2.fileSize  / float(state1.fileSize)

  print()
  print ("Statistics:")
  print ("memoryUsageInfo before compression: " + state1.memoryUsageInfo)
  print ("memoryUsageInfo after compression:  "+ state2.memoryUsageInfo)
  print ("memoryUsageInfo after decompression:  "+ state3.memoryUsageInfo)
  print()
  print ("total time to compress in seconds: %.5f" % totalTimeForCompression.total_seconds() )
  print ("total time to decompress in seconds: %.5f" % totalTimeForDecompression.total_seconds() )
  print()
  print ("uncompressedFileSize in MB:  %.5f" % (state1.fileSize /1024/1024) )
  print ("compressedFileSize in MB:  %.5f" % (state2.fileSize/1024/1024))
  print ("compressionRatio(uncomp/comp):  %.2f" % compressionRatio)


def testWithDetails(compressionModeName,compressionMode):
    print ("<<<#####################################################")
    print ("Compressing with " + compressionModeName)

    prepareParameters(compressionModeName)

    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)


    compressByTar.compress(workingPath, fileNameToBeCompressed ,compressedFileName, compressionMode)

    stateAfterCompression = State(workingPath, compressedFileName)

    decompressByTar.decompress(workingPath, compressedFileName)

    stateAfterDecompression = State(workingPath, compressedFileName)

    printStatistics(stateBeforeCompression, stateAfterCompression,stateAfterDecompression)
    print ("#####################################################>>>")
    return;





print()
print()
print()
testWithDetails('gzip', 'w:gz')
testWithDetails('bzip2', 'w:bz2')
testWithDetails('lzma', 'w:xz')
 
