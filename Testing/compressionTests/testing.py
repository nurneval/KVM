import sys
import datetime
import os
import tarfile
import subprocess


class State:

    def __init__(self, workingPath=None, fileName=None):
        self.currentTime = datetime.datetime.now()
        if workingPath is not None and fileName is not None:
            self.fileSize = os.path.getsize(workingPath + fileName)


def printStatistics(state1=State, state2=State, state3=State, state4=State):
    totalTimeForCompression = state2.currentTime - state1.currentTime
    totalTimeForDecompression = state4.currentTime - state3.currentTime
    compressionRatio = state2.fileSize / float(state1.fileSize)

    print()
    print("Statistics:")
    print()
    print("total time to compress in seconds: %.5f" % totalTimeForCompression.total_seconds())
    print("total time to decompress in seconds: %.5f" % totalTimeForDecompression.total_seconds())
    print()
    print("uncompressedFileSize in MB:  %.5f" % (state1.fileSize / 1024 / 1024))
    print("compressedFileSize in MB:  %.5f" % (state2.fileSize / 1024 / 1024))
    print("compressionRatio(uncomp/comp):  %.2f" % compressionRatio)


def gzip():
    print("<<<#####################################################")
    print("Compressing with gzip ")

    print("compressing :" + workingPath + fileNameToBeCompressed)
    compressedFileName = fileNameToBeCompressed + "_gzip"
    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)
    out = tarfile.open(compressedFileName, mode='w:gz')
    out.add(workingPath + fileNameToBeCompressed)
    out.close()
    stateAfterCompression = State(workingPath, compressedFileName)
    print("compressing finished successfully")

    decompressionPath = workingPath + "decomplar"
    print("Decompressing :" + workingPath + compressedFileName)
    stateBeforeDecompression = State()
    tf = tarfile.open(workingPath + compressedFileName)
    tf.extractall(path=decompressionPath)
    stateAfterDecompression = State()
    print("Decompressing finished successfully")

    printStatistics(stateBeforeCompression, stateAfterCompression, stateBeforeDecompression, stateAfterDecompression)
    print("#####################################################>>>")
    return;


def bzip2():
    print("<<<#####################################################")
    print("Compressing with bzip2 ")

    print("compressing :" + workingPath + fileNameToBeCompressed)
    compressedFileName = fileNameToBeCompressed + "_bzip2"
    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)
    out = tarfile.open(compressedFileName, mode='w:bz2')
    out.add(workingPath + fileNameToBeCompressed)
    out.close()
    stateAfterCompression = State(workingPath, compressedFileName)
    print("compressing finished successfully")

    decompressionPath = workingPath + "decomplar"
    print("Decompressing :" + workingPath + compressedFileName)
    stateBeforeDecompression = State()
    tf = tarfile.open(workingPath + compressedFileName)
    tf.extractall(path=decompressionPath)
    stateAfterDecompression = State()
    print("Decompressing finished successfully")

    printStatistics(stateBeforeCompression, stateAfterCompression, stateBeforeDecompression, stateAfterDecompression)
    print("#####################################################>>>")
    return;


def lzma():
    print("<<<#####################################################")
    print("Compressing with lzma ")

    print("compressing :" + workingPath + fileNameToBeCompressed)
    compressedFileName = fileNameToBeCompressed + "_lzma"
    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)
    out = tarfile.open(compressedFileName, mode='w:xz')
    out.add(workingPath + fileNameToBeCompressed)
    out.close()
    stateAfterCompression = State(workingPath, compressedFileName)
    print("compressing finished successfully")

    decompressionPath = workingPath + "decomplar"
    print("Decompressing :" + workingPath + compressedFileName)
    stateBeforeDecompression = State()
    tf = tarfile.open(workingPath + compressedFileName)
    tf.extractall(path=decompressionPath)
    stateAfterDecompression = State()
    print("Decompressing finished successfully")

    printStatistics(stateBeforeCompression, stateAfterCompression, stateBeforeDecompression, stateAfterDecompression)
    print("#####################################################>>>")
    return;


def lzip():
    print("<<<#####################################################")
    print("Compressing with lzip ")

    print("compressing :" + workingPath + fileNameToBeCompressed)
    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)
    subprocess.call(['lzip', "-kf", workingPath + fileNameToBeCompressed])
    compressedFileName = fileNameToBeCompressed + ".lz"
    stateAfterCompression = State(workingPath, compressedFileName)
    # print("compressing finished successfully")

    print("Decompressing :" + workingPath + compressedFileName)
    stateBeforeDecompression = State()
    subprocess.call(['pigz', '-dkf', workingPath + compressedFileName ])
    stateAfterDecompression = State()
    print("Decompressing finished successfully")

    printStatistics(stateBeforeCompression, stateAfterCompression, stateBeforeDecompression, stateAfterDecompression)
    print("#####################################################>>>")
    return;



def pigz():
    print("<<<#####################################################")
    print("Compressing with pigz ")

    print("compressing :" + workingPath + fileNameToBeCompressed)
    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)
    subprocess.call(['pigz', "-kf", workingPath + fileNameToBeCompressed])
    compressedFileName = fileNameToBeCompressed + ".gz"
    stateAfterCompression = State(workingPath, compressedFileName)
    # print("compressing finished successfully")

    print("Decompressing :" + workingPath + compressedFileName)
    stateBeforeDecompression = State()
    subprocess.call(['pigz', '-dkf', workingPath + compressedFileName ])
    stateAfterDecompression = State()
    print("Decompressing finished successfully")

    printStatistics(stateBeforeCompression, stateAfterCompression, stateBeforeDecompression, stateAfterDecompression)
    print("#####################################################>>>")
    return;




def pbzip2():
    print("<<<#####################################################")
    print("Compressing with pbzip2 ")

    print("compressing :" + workingPath + fileNameToBeCompressed)
    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)
    subprocess.call(['pbzip2', "-kf", workingPath + fileNameToBeCompressed])
    compressedFileName = fileNameToBeCompressed + ".bz2"
    stateAfterCompression = State(workingPath, compressedFileName)
    # print("compressing finished successfully")

    print("Decompressing :" + workingPath + compressedFileName)
    stateBeforeDecompression = State()
    subprocess.call(['pbzip2', '-dkf', workingPath + compressedFileName ])
    stateAfterDecompression = State()
    print("Decompressing finished successfully")

    printStatistics(stateBeforeCompression, stateAfterCompression, stateBeforeDecompression, stateAfterDecompression)
    print("#####################################################>>>")
    return;


def lbzip2():
    print("<<<#####################################################")
    print("Compressing with lbzip2 ")

    print("compressing :" + workingPath + fileNameToBeCompressed)
    stateBeforeCompression = State(workingPath, fileNameToBeCompressed)
    subprocess.call(['lbzip2', "-kf", workingPath + fileNameToBeCompressed])
    compressedFileName = fileNameToBeCompressed + ".bz2"
    stateAfterCompression = State(workingPath, compressedFileName)
    # print("compressing finished successfully")

    print("Decompressing :" + workingPath + compressedFileName)
    stateBeforeDecompression = State()
    subprocess.call(['lbzip2', '-dkf', workingPath + compressedFileName ])
    stateAfterDecompression = State()
    print("Decompressing finished successfully")

    printStatistics(stateBeforeCompression, stateAfterCompression, stateBeforeDecompression, stateAfterDecompression)
    print("#####################################################>>>")
    return;


print()
print()
print()

workingPath = sys.argv[1]
fileNameToBeCompressed = sys.argv[2]
os.chdir(workingPath)

gzip()
bzip2()
lzma()

lzip() # based on LZMA compression algorithm


pigz() # multi-threaded version of gzip
pbzip2()# multi-threaded version of bzip2
lbzip2() #  multi-threaded version of bzip2
#plzip() # multi-threaded version of lzip
##lzop()