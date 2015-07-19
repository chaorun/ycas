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

"""This module performs the reduction of astronomical images. 

It walks the directories looking for bias, flat and data images.
For bias images calculates the average bias.
For flats images, subtract the bias, normalize the result and calculates the 
average flat for each filter.
Finally for each data image subtract bias and divide it by the flat 
corresponding to its filter.
"""

import sys
import os
import logging
import glob
import shutil
from pyraf import iraf
from constants import *

def show_bias_files_statistics(list_of_files):
    """ Show the statistics for the bias files received.
    
    This function applies imstat to the files received and print the results.
    
    Args: 
        list_of_files: List of files to get their statistics.   
    
    """
    
    # Control pyraf exception.
    try:
        # Get statistics for the list of bias files using imstat.
    	means = iraf.imstat(list_of_files, fields='mean', Stdout=1)
    	means = means[IMSTAT_FIRST_VALUE:]
    	mean_strings = [str(m).translate(None, ",\ ") for m in means]
    	mean_values = [float(m) for m in mean_strings]
    	
        # Print the results.
    	logging.debug("Bias images - Max. mean: " + str(max(mean_values)) + \
    			      " Min. mean: " + str(min(mean_values)))	
        
    except iraf.IrafError as exc:
    	logging.error("Error executing imstat: Stats for bias images: " + \
                      list_of_files)
    	logging.error("Iraf error is: " + str(exc))  
        
    except ValueError as ve: 	
        logging.error("Error calculating mean values: " + str(mean_strings))
        logging.error("Error is: " + str(ve))          	

def generate_all_masterbias():
    """ Calculation of all the masterbias files.
    
    This function search for bias files from current directory.
    The bias images are located in specific directories that only
    contains bias images and have a specific denomination, so searching
    for bias files is searching these directories.
    Once a directory for bias had been found a masterbias is calculated
    with an average operation using all the bias files.
    
    """

    logging.info("Generating all masterbias files ...")
    
    # Walk from current directory.
    for path,dirs,files in os.walk('.'):
    	
        # Check if current directory is for bias fits.
        for dr in dirs:
            if dr == BIAS_DIRECTORY:
    				
                # Get the full path of the directory.                
                full_dir = os.path.join(path, dr)
                logging.debug("Found a directory for 'bias': " + full_dir)
                
                # Get the list of files.
                files = glob.glob(os.path.join(full_dir, "*." + FIT_FILE_EXT))
                logging.debug("Found " + str(len(files)) + " bias files")
                
                # Build the masterbias file name.
                masterbias_name = os.path.join(full_dir, MASTERBIAS_FILENAME) 
                
                # Check if masterbias already exists.
                if os.path.exists(masterbias_name) == True:
                    logging.debug("Masterbias file exists, " + \
                                  masterbias_name + \
                                  " so resume to next directory.")
                else:
                    # Put the files list in a string.
                    list_of_files = str(files).translate(None, "[]\'")
                    
                    #show_bias_files_statistics(list_of_files)
                        	
                    # Combine all the bias files.
                    try:
                        logging.debug("Creating bias file: " + \
                                      MASTERBIAS_FILENAME)
                        iraf.imcombine(list_of_files, masterbias_name, Stdout=1)
                        
                    except iraf.IrafError as exc:
                        logging.error("Error executing imcombine: " + \
                                      "Combining bias with: " + list_of_files)  
                        logging.error("Iraf error is: " + str(exc))    
                        
def normalize_flats(files):
    """ Normalize a set of flat files. 
    
    This function receives a list of flat files and returns a list of
    files of the flat files after normalize them.
    The normalization is performed dividing the flat image by the mean
    value of the flat image. This mean is the result of applying imstat
    to each image.
    
    Args: 
        files: The names of the files corresponding to the flat images.
    
    Returns:    
    The list of file names related to the normalized images.
    
    """
    
    # The output list of normalized files is created.
    list_of_norm_flat_files = []
    	
    for fl in files:
        # Get the 'work' and 'normalized' names for the flat files to process.
        work_file = fl.replace("." + FIT_FILE_EXT, \
                               WORK_FILE_SUFFIX + "." + FIT_FILE_EXT)
        
        norm_file = fl.replace("." + FIT_FILE_EXT, \
                               NORM_FILE_SUFFIX + "." + FIT_FILE_EXT)
        
        # Getting statistics for flat file.
        try:
            flat_stats = iraf.imstat(work_file, fields='mean', Stdout=1)
            flat_stats = flat_stats[IMSTAT_FIRST_VALUE]    
            
            try:
                mean_value = float(flat_stats)
                                
                # Normalize flat dividing flat by its mean value.
                iraf.imarith(work_file, '/', mean_value, norm_file)
                
                # If success, add the file to the list of normalized flats.
                list_of_norm_flat_files.extend([norm_file])
    			
            except iraf.IrafError as exc:
                logging.error("Error executing imarith: normalizing flat " + \
                              "image: " + fl)
                logging.error("Iraf error is: " + str(exc))
                
            except ValueError as ve:     
                logging.error("Error calculating mean value for: " + \
                              str(flat_stats))
                logging.error("Error is: " + str(ve))                      
    	
        except iraf.IrafError as exc:
            logging.error("Error executing imstat: getting stats for flat " + \
                          "image: " + fl)
            logging.error("Iraf error is: " + str(exc))       
    
    return list_of_norm_flat_files


def generate_masterflat(full_dir, files, masterflat_name):
    """Generates a master flat from the flat files received.
    
    Args:
        full_dir: Full source path of the flat files.
        files: List of flat files.
        masterflat_name: The name of the masterflat file.
    """
    
    # Put the files list in a string.
    list_of_flat_files = str(files).translate(None, "[]\'")
    
    # Create list of names of the work flat files.
    work_files = [s.replace("." + FIT_FILE_EXT, 
            WORK_FILE_SUFFIX + "." + FIT_FILE_EXT) for s in files]
    
    # Remove braces and quotes from the string.
    list_of_work_flat_files = str(work_files).translate(None, 
        "[]\'")
    
    # Get the masterflat file name.
    masterbias_name = os.path.join(full_dir, 
        PATH_FROM_FLAT_TO_BIAS, 
        MASTERBIAS_FILENAME)
    
    try:
        # Check if masterbias exists.
        if os.path.exists(masterbias_name):
            # Create the work files subtracting bias from flat.
            iraf.imarith(list_of_flat_files, '-', masterbias_name, \
                         list_of_work_flat_files)
        else:
            for i in range(len(files)):
                # Create the work files as a copy of original
                # files.
                shutil.copyfile(files[i], work_files[i])
        
        logging.debug("Normalizing flat files for: " + masterflat_name)
        norm_flat_files = normalize_flats(files)
        
        # After creating the normalized files, remove the work files to save 
        # storage.
        try:
            for wf in work_files:
                os.remove(wf)
                
        except OSError as oe:
            
            logging.error("OSError removing work flat is: " + str(oe))
            
        logging.debug("Creating flat files for: " + masterflat_name)
        
        # Create list of names of the normalized flat files.
        list_of_norm_flat_files = str(norm_flat_files).translate(None, "[]\'")
        
        try:
            iraf.imcombine(list_of_norm_flat_files, masterflat_name, Stdout=1)
            # After calculating the masterflat, remove the normalized files
            # to save storage space.
            for nff in norm_flat_files:
                os.remove(nff) # Combine all the flat files.
        
        except iraf.IrafError as exc:
            logging.error("Error executing imcombine. " + \
                          "Combining flats with: " + list_of_work_flat_files)
            
            logging.error("Iraf error is: " + str(exc))
            
        except OSError as oe:
            logging.error("OSError removing normalized " + "flat is: " + \
                          str(oe))
            
    except iraf.IrafError as exc:
        logging.error("Error executing imarith. " + \
                      "Subtracting masterbias " + masterbias_name + " to: " + \
                      list_of_flat_files)
        
        logging.error("Iraf error is: " + str(exc))

def generate_all_masterflats():
    """ Calculation of all the masterflat files.
    
    This function search for flat files from current directory.
    Usually data images are taken using different filters, so flat images
    are taken using the same filters, and into each flat directory the flat
    images are divides in different directories, one for each filter.
    Once a directory for flat had been found, a bias subtraction is performed
    with each flat image. Finally a masterflat is calculated for each flat 
    directory with an average operation using all the bias files.    
        
    """
    
    logging.info("Generating all masterflats files ...")

    # Walk from current directory.
    for path,dirs,files in os.walk('.'):

        # Process only directories without subdirectories.
        if len(dirs) == 0:
            split_path = path.split(os.sep)

            # Check if current directory is for flats.
            if split_path[-2] == FLAT_DIRECTORY:
                # Get the full path of the directory.                
                full_dir = path
                logging.debug("Found a directory for 'flat': " + full_dir)

                # Get the list of files.
                files = glob.glob(os.path.join(full_dir, "*." + FIT_FILE_EXT))
                logging.debug("Found " + str(len(files)) + " flat files")
                
                # Buid the masterflat file name.
                masterflat_name = os.path.join(full_dir, MASTERFLAT_FILENAME) 
                
                # Check if masterflat already exists.
                if os.path.exists(masterflat_name) == True:
                    logging.debug("Masterflat file exists, " + \
                                  masterflat_name + \
                                  " so resume to next directory.")
                else:
                    generate_masterflat(full_dir, files, masterflat_name)                        

def reduce_image(masterbias_name, masterflat_name, source_image, final_image):
    """Reduce an image.
    
    First the masterbias is subtracted if it exists, and later the image is
    # divided by the flat, if exists.
    These aritmethic operations on the images are performed with imarith.    
    
    Args:
        masterbias_name: The full name of the masterbias file.
        masterflat_name: The full name of the masterflat file.
        source_image:The name of the source image
        final_image: The name for the image reduced.
    """
    
    # Get the work file name, a temporary file to store the result between bias
    # and flat application.
    work_file = source_image.replace("." + FIT_FILE_EXT, \
                                     WORK_FILE_SUFFIX + "." + FIT_FILE_EXT)
    
    # Control imarith exception.
    try:
        # If masterbias exists.
        if len(masterbias_name) > 0:
            # Create the work files subtracting bias
            # from flat.
            iraf.imarith(source_image, '-', masterbias_name, work_file)
        else:
            # Use as work file (the input for flat step) the original file.
            work_file = source_image 
                    
        # Control imarith exception.
        try:
            
            # If masterflat exists.
            if len(masterflat_name) > 0: 
                # Create the final data dividing by master flat.
                iraf.imarith(work_file, "/", masterflat_name, final_image)
            else:
                # In this case the final file is the file resulting from bias 
                # step. It could be even the original file if the masterbias 
                # does not exist.
                shutil.copyfile(work_file, final_image) 
            
            # If the work file is not the original file, and it is really a 
            # temporary file, remove it to save storage space.
            if len(masterbias_name) > 0: 
                os.remove(work_file)
                
        except iraf.IrafError as exc:
            logging.error("Error executing imarith applying flat: " + \
                          work_file + " / " + masterflat_name + \
                          " to " + final_image)
            
            logging.error("Iraf error is: " + str(exc))
            
    except iraf.IrafError as exc:
        logging.error("Error executing imarith applying bias: " + \
                      source_image + " - " + masterbias_name + \
                      " to " + work_file)
        
        logging.error("Iraf error is: " + str(exc))

def reduce_data_images():
    """Reduction all data images.
    
    This function search images from the source directory to reduce then. 
    Once a directory with images has been found, the data images that contains
    are processed to reduce them.
    The reduced images are saved in the same directory but with a different
    name to keep the original file. 
        
    """
    
    logging.info("Starting the reduction of data ...")

    # Walk from current directory.
    for path,dirs,files in os.walk('.'):

        # Inspect only directories without subdirectories.
        if len(dirs) == 0:
            split_path = path.split(os.sep)

            # Check if current directory is for flats.
            if split_path[-2] == DATA_DIRECTORY:
                # Get the full path of the directory.                
                full_dir = path
                logging.debug("Found a directory for data: " + full_dir)

                # Get the list of files.
                data_files = glob.glob(os.path.join(full_dir, "*." + \
                                                    FIT_FILE_EXT))
                logging.debug("Found " + str(len(data_files)) + " data files")
                
                # Get the masterbias file name using the path where it should 
                # exists after organizing the files.
                masterbias_name = \
                    os.path.join(full_dir, PATH_FROM_DATA_TO_BIAS, \
                                 MASTERBIAS_FILENAME)    
                    
                # Check if bias really exists.
                if not os.path.exists(masterbias_name):
                    logging.warning("Masterbias does not exists: " + \
                                    masterbias_name)  
                    masterbias_name = ""
                
                # Get the masterflat file name using the path where it should 
                # exists after organizing the files.
                masterflat_name = \
                    os.path.join(full_dir, PATH_FROM_DATA_TO_FLAT, \
                                 split_path[-1], MASTERFLAT_FILENAME)
                                        
                # Check if bias really exists.
                if not os.path.exists(masterflat_name):
                    logging.warning("Masterflat does not exists: " + \
                                    masterflat_name)  
                    masterflat_name = ""       

                # Reduce each data file one by one.
                for source_image in data_files:     
                    
                    # If current file is not final.
                    if source_image.find(DATA_FINAL_SUFFIX + "." + \
                                         FIT_FILE_EXT) < 0:
                        # Get the name of the final file.
                        final_image = source_image.replace("." + FIT_FILE_EXT, \
                                                   DATA_FINAL_SUFFIX + "." + \
                                                   FIT_FILE_EXT) 
                    else:
                        # The following 'if' will ignore this file for 
                        # reduction.
                        final_image = source_image
                    
                    # Maybe some files can be final already, ignore them.
                    if  os.path.exists(final_image):           
                        logging.debug("Ignoring file for reduction, " + \
                                      "already exists: " + final_image)
                    else:
                        reduce_image(masterbias_name, masterflat_name, \
                                     source_image, final_image)

                        
def reduce_images():
    """Top level function to perform the reduction of data images. 
    
    The tasks are performed sequentially: generate all masterbias, 
    generate all masterflats and finally reduce data images.
    
    """

    # Load the images package and does not show any output of the tasks.
    iraf.images(_doprint=0)

    # Obtain all the average bias.
    generate_all_masterbias()

    # Obtain all the average flat.
    generate_all_masterflats()

    # Reduce data images applying bias and flats.
    reduce_data_images()