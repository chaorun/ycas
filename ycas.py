#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Felipe Gallego. All rights reserved.
#
# This file is part of ycas: https://github.com/felgari/ycas
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Calculates the magnitude of a group of objects in a sequence of steps.

The processing assumes certain values in the header of the fits images,
even in the names of the files. Also a list of objects of interest, 
whose magnitudes are calculated, and a list of standard stars.
Some characteristics of the CCD camera are also needed to calculate
the photometric magnitude of the objects.
"""

import sys
import logging
import logutil
import yargparser
import starsset
import orgfits
import reduction
import astrometry
import photometry
import magnitude
import curves
import summary
from constants import *

def do_summary(progargs):
    """ Generates a summary for the tasks performed by the pipeline.
    
    Args:
        progargs: The program arguments.
        
    """    
    
    # Object that generates the summary.     
    sum_task = summary.SummaryTasks()     
    
    if progargs.all_steps_requested: 
        sum_task.enable_all_summary_task()

    else:    
        if progargs.organization_requested:
            sum_task.enable_organization_summary
    
        if progargs.reduction_requested:
            sum_task.enable_reduction_summary
            
        if progargs.astrometry_requested:
            sum_task.enable_astrometry_summary   
            
        if progargs.photometry_requested:
            sum_task.enable_photometry_summary
            
        if progargs.diff_photometry_requested:
            sum_task.enable_diff_photometry_summary
            
        if progargs.magnitudes_requested:
            sum_task.enable_magnitude_summary

    sum_task.generate_summary()    

def pipeline(progargs):
    """ Performs sequentially the steps of the pipeline that have been 
    requested.
    
    Args:
        progargs: The program arguments.
        
    """
    
    stars = None
    # Magnitudes calculated.
    mag = None
    
    if progargs.file_of_stars_provided:        
        # Read the data of the stars of interest.
        stars = starsset.StarsSet(progargs.stars_file_name)        
    
    # This step organizes the images in directories depending on the type of
    # image: bias, flat or data.
    if progargs.organization_requested or progargs.all_steps_requested:
        logging.info("* Step 1 * Organizing image files in directories.")
        orgfits.organize_files(progargs)
        anything_done = True
    else:
        logging.info("* Step 1 * Skipping the organization of image files in directories. Not requested.")
    
    # This step reduces the data images applying the bias and flats.
    if progargs.reduction_requested or progargs.all_steps_requested:
        logging.info("* Step 2 * Reducing images.")
        reduction.reduce_images(progargs)
        anything_done = True
    else:
        logging.info("* Step 2 * Skipping the reduction of images. Not requested.")
        
    # This step find objects in the images. The result is a list of x,y and
    # AR,DEC coordinates.
    if progargs.astrometry_requested or progargs.all_steps_requested:
        logging.info("* Step 3 * Performing astrometry of the images.")
        astrometry.do_astrometry(progargs, stars)
        anything_done = True
    else:
        logging.info("* Step 3 * Skipping astrometry. Not requested.")

    # This step calculates the photometry of the objects detected doing the
    # astrometry.
    if progargs.photometry_requested or progargs.all_steps_requested:
        logging.info("* Step 4 * Performing photometry of the stars.")
        photometry.calculate_photometry(progargs)
        anything_done = True
    else:
        logging.info("* Step 4 * Skipping photometry. Not requested.")
        
    # This step calculates the differental photometry of the objects detected
    # doing the astrometry.
    if progargs.diff_photometry_requested or progargs.all_steps_requested:
        logging.info("* Step 5 * Performing differential photometry.")
        photometry.differential_photometry(progargs)
        anything_done = True
    else:
        logging.info("* Step 5 * Skipping differential photometry of stars. Not requested.")
        
    # This step process the magnitudes calculated for each object and
    # generates a file that associate to each object all its measures.
    if progargs.magnitudes_requested or progargs.all_steps_requested:
        logging.info("* Step 6 * Calculating magnitudes of stars.")
        mag = magnitude.process_magnitudes(stars, progargs.data_directory)
        anything_done = True
    else:
        logging.info("* Step 6 * Skipping the calculation of magnitudes of stars. Not requested.")
        
    # This step process the magnitudes calculated for each object and
    # generates a light curves.
    if progargs.light_curves_requested or progargs.all_steps_requested:
        logging.info("* Step 7 * Generating light curves.")
        curves.generate_curves(stars, mag)
        anything_done = True
    else:
        logging.info("* Step 7 * Skipping the generation of light curves. Not requested.")        
        
    # Generates a summary if requested and some task has been indicated.
    if anything_done and progargs.summary_requested:
        do_summary(progargs)

def main(progargs):
    """ Main function.

    A main function allows the easy calling from other modules and also from 
    the command line.
    
    This function performs all the steps needed to process the images.
    Each step is a calling to a function that implements a concrete task.

    """    
    
    try:
        # Process program arguments checking that programs arguments used are
        # coherent.
        progargs.process_program_arguments()           
        
        # Initializes logging.
        logutil.init_log(progargs)
        
        # Perform the steps requested.
        pipeline(progargs)
        
    except yargparser.ProgramArgumentsException as pae:
        # To stdout, since logging has not been initialized.
        print pae
  

# Where all begins ...
if __name__ == "__main__":

    # Create object to process the program arguments.
    progargs = yargparser.ProgramArguments()    
    
    # Check the number of arguments received.
    if len(sys.argv) <= progargs.min_number_args:
        
        # If no arguments are provided show help and exit.
        print "The number of program arguments are not enough."   
             
        progargs.print_help()
        
        sys.exit(1)
        
    else: 
        # Number of arguments is fine, execute main function.
        sys.exit(main(progargs))