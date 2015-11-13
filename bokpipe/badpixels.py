#!/usr/bin/env python

import os
import numpy as np
from scipy.ndimage.morphology import binary_dilation,binary_closing
from astropy.stats import sigma_clip
import fitsio

from .bokutil import rebin,BokMefImage,BokProcess

bok_badcols = {
  'IM11':range(987,994)+range(1837,1839),
}

class BadPixelMaskFromFlats(BokProcess):
	def __init__(self,**kwargs):
		super(BadPixelMaskFromFlats,self).__init__(**kwargs)
		kwargs.setdefault('header_key','BPMSK')
		self.loCut,self.hiCut = kwargs.get('good_range',(0.90,1.10))
		self.loCut2,self.hiCut2 = kwargs.get('grow_range',(0.95,1.05))
		self.addBadCols = kwargs.get('add_bad_cols',True)
		self.noConvert = True  # casting to unsigned int below
	def process_hdu(self,extName,data,hdr):
		im = np.ma.masked_array(data,mask=((data<0.5) | (data>1.5)))
		# mask the edges
		margin = 15
		im.mask[:margin] = True
		im.mask[-margin:] = True
		im.mask[:,:margin] = True
		im.mask[:,-margin:] = True
		if extName == 'IM9':
			# this one has a long bad strip
			im.mask[:,:50] = True
		badpix = (im < self.loCut) | (im > self.hiCut)
		badpix |= binary_dilation(badpix,
		                          mask=((im<self.loCut2)|(im>self.hiCut2)),
		                          iterations=0)
		badpix |= binary_closing(badpix,iterations=0)
		# add fixed set of bad columns
		if self.addBadCols:
			try:
				jj = bok_badcols[extName]
				print 'masking ',jj,' on ',extName
				badpix[:,jj] |= True
			except KeyError:
				pass
		return badpix.astype(np.uint8),hdr

def build_mask_from_flat(flatFn,outFn,**kwargs):
	bpmGen = BadPixelMaskFromFlats(output_map=lambda f: outFn,
	                               **kwargs)
	bpmGen.process_files([flatFn,])



def make_sextractor_gain_map(flatFn,bpMaskFn,gainMapFn,**kwargs):
	flat = BokMefImage(flatFn,output_file=gainMapFn,**kwargs)
	mask = fitsio.FITS(bpMaskFn)
	for extName,data,hdr in flat:
		# invert the mask, makes bad pixels = 0
		data *= (1 - mask[extName].read())
		flat.update(data,hdr)
	flat.close()
