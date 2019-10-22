#!/usr/bin/env python

import os
import shutil
import glob
import subprocess
from copy import copy
import numpy as np
from astropy.io import fits

configDir = os.path.join(os.path.split(__file__)[0],'config')

def read_cnfg(configName):
	# read a scamp configuration file into a dictionary
	cnfg={}
	with open(configName) as f:
		lines=f.readlines()
		for line in lines:
			# ignore empty lines
			if not( line.strip() ):
				continue
			# ignore commented lines
			if line.strip()[0]=='#':
				continue
			split = line.split(' ',1)
			key=split[0]
			# ignore comments
			split = split[1].split('#',1)
			val=split[0].strip()
			cnfg[key]=val

	return cnfg

def put_wcs(imageFile,verbose=0):
	configFile = os.path.join(configDir,'wcsput.missfits')
	missfits_cmd = ['missfits','-c',configFile,imageFile]
	if verbose > 1:
		print ' '.join(missfits_cmd)
	rv = subprocess.call(missfits_cmd)

def scamp_solver(imageFile,catFile,verbose,**kwargs):
	scamp_cmd_base = ['scamp',catFile,
	                  '-c',os.path.join(configDir,'boksolve.scamp')]
	
	def add_scamp_pars(scamp_pars):
		scamp_cmd = copy(scamp_cmd_base)
		for k,v in scamp_pars.items():
			scamp_cmd.extend(['-'+k,str(v)])
		return scamp_cmd

	# copy in options passed from command-line (override existing)
	scamp_pars = {}
	for k,v in kwargs.items():
		scamp_pars[k] = v
	scamp_cmd = add_scamp_pars(scamp_pars)
	if verbose >= 1:
		outdev = None
		if verbose >=2:
			print ' '.join(scamp_cmd)
	else:
		outdev = open(os.devnull,'w')

	rv = subprocess.call(scamp_cmd,stdout=outdev)

def scamp_solve(imageFile,catFile,wcsCnfg,savewcs=False,clobber=False,verbose=0):

	headf = catFile.replace('.fits','.head') 
	tmpAhead = catFile.replace('.fits','.ahead')
	wcsFile = imageFile.replace('.fits','.ahead')
	if not clobber and os.path.exists(wcsFile):
		if verbose > 0:
			print wcsFile,' already exists, skipping'
		return
	try:
		os.unlink(wcsFile)
	except:
		pass

	for n, cnfg in enumerate(wcsCnfg):
		scamp_pars = read_cnfg(cnfg)
		if verbose >= 1:
			print 'scamp_solve pass', '%i of %i for' % (n+1,len(wcsCnfg)), imageFile
		scamp_solver(imageFile,catFile,verbose,**scamp_pars)
		shutil.move(headf,tmpAhead)
	
	shutil.move(tmpAhead,wcsFile)
	if savewcs:
		put_wcs(imageFile,verbose=verbose)
	return

def scamp_default_solve(imageFile,catFile,refStarCatFile=None,
			filt='g',savewcs=False,clobber=False,
			check_plots=False,twopass=True,verbose=0):

	headf = catFile.replace('.fits','.head') 
	wcsFile = imageFile.replace('.fits','.ahead')
	if not clobber and os.path.exists(wcsFile):
		if verbose > 0:
			print wcsFile,' already exists, skipping'
		return
	if refStarCatFile is not None:
		refCatPath = os.path.dirname(refStarCatFile)
		if len(refCatPath)==0:
			refCatPath = '.'

	try:
		os.unlink(wcsFile)
	except:
		pass
	#
	# FIRST PASS
	#
	scamp_pars = {
	  'DISTORT_DEGREES':1,
	  'ASTRCLIP_NSIGMA':3.0,
	  'CHECKPLOT_TYPE':'NONE',
	}
	if verbose >= 5:
		scamp_pars['VERBOSE_TYPE'] = 'FULL'
	elif verbose >= 1:
		scamp_pars['VERBOSE_TYPE'] = 'NORMAL'
	if refStarCatFile is not None and os.path.exists(refStarCatFile):
		scamp_pars['ASTREFCAT_NAME'] = refStarCatFile
		scamp_pars['ASTREF_CATALOG'] = 'FILE'
	else:
		scamp_pars['ASTREF_CATALOG'] = 'SDSS-R9'
		print scamp_pars['ASTREF_CATALOG']
		scamp_pars['ASTREF_BAND'] = filt
		if refStarCatFile is not None:
			scamp_pars['SAVE_REFCATALOG'] = 'Y'
		# see below
		#scamp_pars['ASTREFCAT_NAME'] = os.path.basename(refStarCatFile)
		#scamp_pars['REFOUT_CATPATH'] = refCatPath
	if verbose >= 1:
		print 'first pass scamp_solve for ',imageFile
	scamp_solver(imageFile,catFile,verbose,**scamp_pars)

	tmpAhead = catFile.replace('.fits','.ahead') 
	shutil.move(headf,tmpAhead)
	if refStarCatFile is not None and scamp_pars['ASTREF_CATALOG'] != 'FILE':
		# scamp automatically names the cached reference file, and as far
		# as I can tell ignores the value of ASTREFCAT_NAME
		# take the auto-saved file and rename it
		tmpfn = min(glob.iglob('%s_*.cat'%scamp_pars['ASTREF_CATALOG']),
		            key=os.path.getctime)
		if verbose > 0:
			print 'tmpfn=',tmpfn
		shutil.move(tmpfn,refStarCatFile)
	if not twopass:
		shutil.move(tmpAhead,wcsFile)
		if savewcs:
			put_wcs(imageFile,verbose=verbose)
		return
	#
	# SECOND PASS
	#
	if refStarCatFile is not None:
		scamp_pars['ASTREF_CATALOG'] = 'FILE'
		scamp_pars['ASTREFCAT_NAME'] = refStarCatFile
	try:
		del scamp_pars['ASTREF_BAND']
	except:
		pass
	scamp_pars['SAVE_REFCATALOG'] = 'N'
	scamp_pars['POSITION_MAXERR'] = 0.25
	scamp_pars['POSANGLE_MAXERR'] = 0.5
	scamp_pars['CROSSID_RADIUS'] = 5.0
	scamp_pars['DISTORT_DEGREES'] = 3
	scamp_pars['MOSAIC_TYPE'] = 'FIX_FOCALPLANE'
	if check_plots:
		del scamp_pars['CHECKPLOT_TYPE']
	
	if verbose > 1:
		print 'second pass scamp_solve for ',imageFile
	scamp_solver(imageFile,catFile,verbose,**scamp_pars)
	
	shutil.move(headf,wcsFile)
	os.unlink(tmpAhead)
	#
	if savewcs:
		put_wcs(imageFile,verbose=verbose)

def read_headers(aheadFile):
	endLine = "END     \n"
	with open(aheadFile,'r') as f:
		hdrText = f.read()
	hdrs = []
	for hstr in hdrText.split(endLine)[:-1]:
		h = fits.Header.fromstring(hstr,sep='\n')
		hdrs.append(h)
	return hdrs

