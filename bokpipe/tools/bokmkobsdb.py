#!/usr/bin/env python

import os
import argparse

from bokpipe import bokobsdb

parser = argparse.ArgumentParser()
parser.add_argument("inputDirs",type=str,nargs='+',
                    help="directories containing FITS images")
parser.add_argument("-o","--output",type=str,default="boklog.fits",
                    help="output log file")
parser.add_argument("-f","--filters",type=str,
                    help="filter list")
parser.add_argument("-e","--extra",type=str,
                    help="list of extra header cards to extract and dtypes"
                         " [e.g., 'HDRCARD:f4,...']")
args = parser.parse_args()

xargs = args.extra.split(',')
xargs_names = tuple([x.split(':')[0] for x in xargs])
xargs_dtypes = tuple([x.split(':')[1] for x in xargs])

def xargs_remap(c,v):
	if c=='DTACQNAM':
		return os.path.basename(v)
	else:
		return v

bokobsdb.generate_log(args.inputDirs,args.output,
                      filters=args.filters,
                      objFilter=None,
                      filePattern=None,
                      extraFields=xargs_names,extraTypes=xargs_dtypes,
                      extra_cb=xargs_remap)

