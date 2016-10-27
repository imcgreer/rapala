#!/usr/bin/env python

import os,sys
import numpy as np
from astropy.stats import sigma_clip
import fitsio

from bokpipe.bokproc import BokImStat

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("inputFiles",type=str,nargs='+',
                    help="input FITS images")
parser.add_argument("-e","--ext",type=str,default="all",
                    help="select FITS extension(s) [default=all]")
parser.add_argument("-s","--statsreg",type=str,
                    help="image region to calculate stats on")
parser.add_argument("--oscan",action="store_true",
                    help="do a simple overscan subtraction")
args = parser.parse_args()

if args.ext=='all':
	extns = None
else:
	extns = args.ext.split(',')

imstat = BokImStat(extensions=extns,quickprocess=args.oscan,
                   stats_region=args.statsreg)
imstat.process_files(args.inputFiles)

#np.set_printoptions(precision=2,suppress=True)

printarr = lambda a: ' '.join(map(lambda x: '%6.2f'%x,a))

for i,fn in enumerate(args.inputFiles):
	print os.path.basename(fn),
	print printarr(imstat.meanVals[i]),
	print printarr(imstat.rmsVals[i])


