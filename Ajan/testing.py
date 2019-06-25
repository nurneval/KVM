
import sys
import datetime

import compressByTar
import memoryUsage



fileNameToBeCompressed= sys.argv[1]


def compressWithDetails(fileNameToBeCompressed,compressedModeName,compressionMode):
    print '######################'
    print 'Compressing with ' + compressedModeName
    startTime= datetime.datetime.now()

    print memoryUsage.using('1memory usage for '  + compressedModeName)
    compressByTar.compress(fileNameToBeCompressed, compressedModeName + '.tar', 'w:gz')
    print memoryUsage.using('2memory usage for '  + compressedModeName)

    finishTime=  datetime.datetime.now()
    timeDelta= finishTime -startTime
    print 'total time in miliseconds: ' + str(timeDelta.total_seconds()*1000)
    print '####################################'
    return;




compressWithDetails(fileNameToBeCompressed, 'gzip', 'w:gz')
compressWithDetails(fileNameToBeCompressed, 'bzip2', 'w:bz2')
