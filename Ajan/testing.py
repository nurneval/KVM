
import sys
import datetime
import os


import compressByTar
import memoryUsage

fullFilePathToBeCompressed= ''
compressedFileName= ''
fullFilePathOfCompressedFile= ''


class State:

  def __init__(self,fullFilePath):
    self.currentTime = datetime.datetime.now()
    self.fileSize = os.path.getsize(fullFilePath) /1024 /1024  ##MB
    self.memoryUsageInfo = memoryUsage.using()


def prepareParameters(compressionModeName):

    global fullFilePathToBeCompressed
    global compressedFileName
    global fullFilePathOfCompressedFile

    workingPath= sys.argv[1]
    fileNameToBeCompressed= sys.argv[2]

    fullFilePathToBeCompressed= workingPath +   fileNameToBeCompressed
    compressedFileName= compressionModeName + '.tar'
    fullFilePathOfCompressedFile= workingPath   + compressedFileName




def printStatistics(state1=State ,  state2=State):
  timeDelta= state2.currentTime - state1.currentTime
  compressionRatio= state2.fileSize  / float(state1.fileSize)


  print ("Statistics:")
  print ("memoryUsageInfo before: " + state1.memoryUsageInfo)
  print ("memoryUsageInfo after:  "+ state2.memoryUsageInfo)
  print ("total time in seconds: " + str(timeDelta.total_seconds()))
  print ("total time in seconds: %.2f" % timeDelta.total_seconds() )
  print ("uncompressedFileSize in MB:  %.2f" % state1.fileSize)
  print ("compressedFileSize in MB:  %.2f" % state2.fileSize)
  print ("compressionRatio:  %.2f" % compressionRatio)


def compressWithDetails(compressionModeName,compressionMode):
    print ("<<<#####################################################")
    print ("Compressing with " + compressionModeName)


    prepareParameters(compressionModeName)

    stateBefore = State(fullFilePathToBeCompressed)

    compressByTar.compress(fullFilePathToBeCompressed,fullFilePathOfCompressedFile, compressionMode)

    stateAfter = State(fullFilePathOfCompressedFile)

    printStatistics(stateBefore, stateAfter)
    print ("#####################################################>>>")
    return;



print()
print()
print()
compressWithDetails('gzip', 'w:gz')
compressWithDetails('bzip2', 'w:bz2')
compressWithDetails('lzma', 'w:xz')

#deleteTarFilesFromWorkingPath(workingPath)
