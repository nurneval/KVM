
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
    self.fileSize = os.path.getsize(fullFilePath)
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
  compressionRatio= state1.fileSize  / float(state2.fileSize)


  print 'Statistics:'
  print 'memoryUsageInfo before: ' + state1.memoryUsageInfo
  print 'total time in miliseconds: ' + str(timeDelta.total_seconds()*1000)
  print 'uncompressedFileSize: ' + str(state1.fileSize)
  print 'compressedFileSize: ' + str(state2.fileSize)
  print 'compressionRatio: ' + str(compressionRatio)
  print 'memoryUsageInfo after: ' + state2.memoryUsageInfo



def compressWithDetails(compressionModeName,compressionMode):
    print '<<<#####################################################'
    print 'Compressing with ' + compressionModeName


    prepareParameters(compressionModeName)

    stateBefore = State(fullFilePathToBeCompressed)

    compressByTar.compress(fullFilePathToBeCompressed,fullFilePathOfCompressedFile, compressionMode)

    stateAfter = State(fullFilePathOfCompressedFile)

    printStatistics(stateBefore, stateAfter)
    print '#####################################################>>>'
    return;



print
print
print
compressWithDetails('gzip', 'w:gz')
compressWithDetails('bzip2', 'w:bz2')

#deleteTarFilesFromWorkingPath(workingPath)
