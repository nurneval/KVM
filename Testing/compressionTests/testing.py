
import sys
import datetime
import os
import tarfile
import subprocess



class State:

  def __init__(self, workingPath, fileName):

    self.currentTime = datetime.datetime.now()
    print (datetime.datetime.now())
    self.fileSize = os.path.getsize(workingPath+fileName)


def printStatistics(state1=State ,  state2=State, state3= State):
  totalTimeForCompression= state2.currentTime - state1.currentTime
  totalTimeForDecompression= state3.currentTime - state2.currentTime
  compressionRatio= state2.fileSize  / float(state1.fileSize)

  print()
  print ("Statistics:")
  print()
  print ("total time to compress in seconds: %.5f" % totalTimeForCompression.total_seconds() )
  print ("total time to decompress in seconds: %.5f" % totalTimeForDecompression.total_seconds() )
  print()
  print ("uncompressedFileSize in MB:  %.5f" % (state1.fileSize /1024/1024) )
  print ("compressedFileSize in MB:  %.5f" % (state2.fileSize/1024/1024))
  print ("compressionRatio(uncomp/comp):  %.2f" % compressionRatio)


def gzip():

    print ("<<<#####################################################")
    print ("Compressing with gzip ")

    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)

    print ("compressing :" + workingPath + fileNameToBeCompressed  )
    compressedFileName= fileNameToBeCompressed + "_gzip"
    out = tarfile.open(compressedFileName, mode='w:gz')
    out.add(fileNameToBeCompressed)
    out.close()
    print ("compressing finished successfully" )


    stateAfterCompression = State(workingPath, compressedFileName)

    decompressionPath = workingPath+ "/decomplar"
    print ("Decompressing :" + workingPath + compressedFileName   )
    tf = tarfile.open(compressedFileName)
    tf.extractall(decompressionPath)
    print ("Decompressing finished successfully" )

    stateAfterDecompression = State(workingPath, compressedFileName)

    printStatistics(stateBeforeCompression, stateAfterCompression,stateAfterDecompression)
    print ("#####################################################>>>")
    return;

def bzip2():

    print ("<<<#####################################################")
    print ("Compressing with bzip2 ")

    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)

    print ("compressing :" + workingPath + fileNameToBeCompressed  )
    compressedFileName= fileNameToBeCompressed + "_bzip2"
    out = tarfile.open(compressedFileName, mode='w:bz2')
    out.add(fileNameToBeCompressed)
    out.close()
    print ("compressing finished successfully" )


    stateAfterCompression = State(workingPath, compressedFileName)

    decompressionPath = workingPath+ "/decomplar"
    print ("Decompressing :" + workingPath + compressedFileName   )
    tf = tarfile.open(compressedFileName)
    tf.extractall(decompressionPath)
    print ("Decompressing finished successfully" )

    stateAfterDecompression = State(workingPath, compressedFileName)

    printStatistics(stateBeforeCompression, stateAfterCompression,stateAfterDecompression)
    print ("#####################################################>>>")
    return;

def lzma():

    print ("<<<#####################################################")
    print ("Compressing with bzip2 ")

    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)

    print ("compressing :" + workingPath + fileNameToBeCompressed  )
    compressedFileName= fileNameToBeCompressed + "_lzma"
    out = tarfile.open(compressedFileName, mode='w:xz')
    out.add(fileNameToBeCompressed)
    out.close()
    print ("compressing finished successfully" )


    stateAfterCompression = State(workingPath, compressedFileName)

    decompressionPath = workingPath+ "/decomplar"
    print ("Decompressing :" + workingPath + compressedFileName   )
    tf = tarfile.open(compressedFileName)
    tf.extractall(decompressionPath)
    print ("Decompressing finished successfully" )

    stateAfterDecompression = State(workingPath, compressedFileName)

    printStatistics(stateBeforeCompression, stateAfterCompression,stateAfterDecompression)
    print ("#####################################################>>>")
    return;


def pbzip2():

    print ("<<<#####################################################")
    print ("Compressing with pbzip2 ")

    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)

    print ("compressing :" + workingPath + fileNameToBeCompressed  )
    subprocess.call(['pbzip2',"-kf" , fileNameToBeCompressed ])
    compressedFileName=fileNameToBeCompressed + ".bz2"
    print ("compressing finished successfully" )

    stateAfterCompression = State(workingPath, compressedFileName)


    print ("Decompressing :" + workingPath + compressedFileName  )
    subprocess.call(['pbzip2','-df',  compressedFileName ])
    print ("Decompressing finished successfully" )

    stateAfterDecompression = State(workingPath, fileNameToBeCompressed)

    printStatistics(stateBeforeCompression, stateAfterCompression,stateAfterDecompression)
    print ("#####################################################>>>")
    return;





print()
print()
print()


workingPath= sys.argv[1]
fileNameToBeCompressed= sys.argv[2]
os.chdir(workingPath)


gzip()
bzip2()
lzma()
pbzip2()
#testWithDetails('pbzip2', '')
#testWithDetails('gzip', 'w:gz')
#testWithDetails('bzip2', 'w:bz2')
#testWithDetails('lzma', 'w:xz')
