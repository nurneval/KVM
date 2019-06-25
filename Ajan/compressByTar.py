
import tarfile

import sys
<<<<<<< HEAD


=======
 
>>>>>>> 5392d319d51a9fe316f0c67f68921f952cae0346
def compress( fileNameToBeCompressed,compressedFileName, compressionMode  ):
    print 'creating archive:' + compressedFileName
    out = tarfile.open(compressedFileName, mode='w:gz')
    try:
	    print 'adding ' + fileNameToBeCompressed
	    out.add(sys.argv[1])
    finally:
        print 'closing ' + compressedFileName
        out.close()

	print
	print 'Contents added to '  + compressedFileName +' :'
	t = tarfile.open(compressedFileName, 'r')
	for member_info in t.getmembers():
	    print member_info.name
    return;
