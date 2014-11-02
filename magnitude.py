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

"""
This module obtains the magnitude of a set of object using the photometry
values calculated previously.
The magnitude values are stored in different files for each object.
"""

import sys
import os
import logging
import yargparser
import glob
import pyfits
import csv
from constants import *
import numpy as np
from scipy import stats

def get_object_name_from_rdls(rdls_file):
    
    # From the file name get the name of the object.
    object_name_with_path = rdls_file[0:rdls_file.find(DATANAME_CHAR_SEP)]
     
    return os.path.basename(object_name_with_path)     

def get_ra_dec_for_object(objects, object_name):
    """
    
    This function receives the name of an object and the set of objects
    and returns the coordinates for that object contained in the
    list of objects.
    
    """
    
    ra = 0.0
    dec = 0.0
    
    for obj in objects:
        if obj[OBJ_NAME_COL] == object_name:
            ra = float(obj[OBJ_RA_COL])
            dec = float(obj[OBJ_DEC_COL])
    
    return ra, dec

def read_objects_of_interest(progargs):
    """
        
    Read the list of objects of interest from the file indicated.
    This file contains the name of the object and the AR, DEC 
    coordinates of each object.
    
    """
    
    objects = list()
    
    # Read the file that contains the objects of interest.
    with open(progargs.interest_object_file_name, 'rb') as fr:
        reader = csv.reader(fr, delimiter='\t')        
        
        for row in reader:    
            objects.append(row)   
            
    logging.info("Read the following objects: " +  str(objects))            
            
    return objects     

def get_rdls_data(rdls_file):
    """
    
    This function returns the AR, DEC values stores in a RDLS
    file generated during the photometry step.
    This file is a FIT file that contains a table and this
    function returns the values in a list.
    
    """
    
    # Open the FITS file received.
    fits_file = pyfits.open(rdls_file) 

    # Assume the first extension is a table.
    tbdata = fits_file[1].data       
    
    fits_file.close
    
    # Convert data from fits table to a list.
    ldata = list()
    
    # To add an index to the rows.
    n = 1
    
    for row in tbdata:
        ldata.append([n, row[0], row[1]])
        n += 1
    
    return ldata  

def get_object_references(rdls_file, objects):
    """
    
    This function takes and RDLS file and a list of objects and 
    returns the index in the RDLS file whose coordinates get the
    better match for those of the object and also the name of the
    object.
    
    """
    
    index = -1
    
    # Get the name of the object related to this RDLS file.
    object_name = get_object_name_from_rdls(rdls_file)
    
    # Get coordinates for the object related to the RDLS file.
    ar, dec = get_ra_dec_for_object(objects, object_name)    
    
    # Get RDLS data.
    rdls_data = get_rdls_data(rdls_file) 
    
    ra_diff = 1000.0
    dec_diff = 1000.0 
    
    i = 0
    for rd in rdls_data:
        # Compute the difference between the coordinates of the
        # object in this row and the object received.  
        temp_ra_diff = abs(float(rd[RDLS_RA_COL_NUMBER]) - ar)
        temp_dec_diff = abs(float(rd[RDLS_DEC_COL_NUMBER]) - dec)   
        
        # If current row coordinates are smaller than previous this
        # row is chosen as candidate for the object.
        if temp_ra_diff < ra_diff and temp_dec_diff < dec_diff:
            ra_diff = temp_ra_diff
            dec_diff = temp_dec_diff
            index = i        
    
        i += 1
        
    logging.info("Found index for object " + object_name + " at " + str(index))
        
    return index, object_name    

def get_inst_magnitudes_for_object(rdls_file, path, objects):
    """
    
    This function search in a given path all the files related to
    an object that contains magnitudes for that object.
    
    """
    
    # Get the index of this object in the files that contains the magnitudes.
    object_index, object_name = get_object_references(rdls_file, objects)
    
    # Get the list of files with magnitudes for the images of this object.
    # At this point all the csv are related to magnitude values. 
    csv_files = glob.glob(os.path.join(path, object_name + "*." + CSV_FILE_EXT))
    
    # The name of the directory that contains the file is the name of the filter
    path_head, filter_name = os.path.split(path)
    
    logging.info("Found " + str(len(csv_files)) + " csv files for object " \
                 + object_name)
    
    # Sort the list of csv files to ensure a right processing.
    csv_files.sort()
    
    # To store the magnitudes.
    magnitudes = list()
    
    # Read magnitudes from csv files and add it to RDLS data.
    # Each csv file contains the magnitudes for all the object of an image.
    for csv_fl in csv_files:
        
        with open(csv_fl, 'rb') as fr:
            reader = csv.reader(fr)
            
            nrow = 0
            
            for row in reader:
            
                # Check if current row corresponds to the object.
                if nrow == object_index:
                    # Get a list of values from the CSV row read.
                    fields = str(row).translate(None, "[]\'").split()
                    
                    # Add magnitude value to the appropriate row from RDLS file.
                    magnitudes.append([fields[CSV_TIME_COL], 
                                         fields[CSV_MAG_COL],
                                         fields[CSV_AIRMASS_COL], 
                                         filter_name])
                
                nrow += 1
                
    return magnitudes 

def save_magnitudes(object_name, filename_sufix, inst_magnitudes_obj):
    """
    
    Save the magnitudes to a text file.
    
    """
    
    # Get the name of the output file.
    output_file_name = object_name + filename_sufix + "." + TSV_FILE_EXT

    with open(output_file_name, 'w') as fw:
        
        writer = csv.writer(fw, delimiter='\t')

        # It is a list that contains sublists, each sublist is
        # a different magnitude, so each one is written as a row.
        for imag in inst_magnitudes_obj:
        
            # Write each magnitude in a row.
            writer.writerows(imag)  

def compile_instrumental_magnitudes(objects):
    """
    
    This function receives a list of object and compiles all the magnitudes
    found in a text file for each object.
    
    """
    
    # For each object a list is created to store its magnitudes.
    # In turn, all these lists are grouped in a list. 
    instrumental_magnitudes = list()
    
    # Create a dictionary to retrieve easily the appropriate list
    # using the name of the object.
    objects_index = {}
    
    for i in range(len(objects)):
        instrumental_magnitudes.append([])
        
        objects_index[objects[i][OBJ_NAME_COL]] = i
        
    # Walk all the directories searching for files containing magnitudes.
    # Walk from current directory.
    for path,dirs,files in os.walk('.'):

        # Inspect only directories without subdirectories.
        if len(dirs) == 0:
            split_path = path.split(os.sep)

            # Check if current directory is for data.
            if split_path[-2] == DATA_DIRECTORY:
               
                logging.info("Found a directory with data images: " + path)

                # Get the list of RDLS files ignoring hidden files.
                rdls_files_full_path = \
                    [f for f in glob.glob(os.path.join(path, "*." + RDLS_FILE_EXT)) \
                    if not os.path.basename(f).startswith('.')]
                    
                logging.info("Found " + str(len(rdls_files_full_path)) + \
                             " RDLS files")        

                # Process the images of each object that has a RDLS file.
                for rdls_file in rdls_files_full_path:
                    
                    # Get the magnitudes for this object in current path.
                    im = get_inst_magnitudes_for_object(rdls_file, path, objects)
                    
                    # If any magnitude has been get.
                    if len(im) > 0:
                        # Get the name of the object.
                        object_name = get_object_name_from_rdls(rdls_file)                    
                        
                        try:
                            # Retrieve the list that contains the magnitudes 
                            # for this object.
                            magnitudes_index = objects_index[object_name]
                        
                            object_mea_list = instrumental_magnitudes[magnitudes_index]
                        
                            # Add the magnitude to the object.
                            object_mea_list.append(im)
                        except KeyError as ke:
                            logging.error("RDLS file with no object of interest: " + \
                                          object_name)
                        
    return instrumental_magnitudes  
            
def get_day_of_measurement(time_jd):
    """
    
    Returns the julian day that is assigned to this value.
    The day is assigned to that which the night begins.
    So a JD between .0 (0:00:00) and .4 (+8:00:00) belongs 
    to the day before.
    
    """    
    
    day = None
    
    dot_pos = time_jd.find('.')
    
    first_decimal = time_jd[dot_pos + 1]
    
    int_first_decimal = int(first_decimal) 
    
    if int_first_decimal >= 0 and int_first_decimal <= 4:
        day = str(int(time_jd[:dot_pos]) - 1)
    else:
        day = time_jd[:dot_pos]
    
    return day

def get_standard_magnitude(object_data, filter):
    """
    
    Get the standard magnitude of an object in the filter indicated.
    
    """
    
    std_mag = None
    
    # Depending on the filter name received get the appropriate column.
    if filter == B_FILTER_NAME:
        std_mag = object_data[OBJ_B_MAG_COL]
    elif filter == V_FILTER_NAME:
        std_mag = object_data[OBJ_V_MAG_COL]      
    elif filter == R_FILTER_NAME:
        std_mag = object_data[OBJ_R_MAG_COL]       
        
    return std_mag

def calculate_extinction_coefficient(mag_data):
    """
    
    Calculate the extinction coefficient using the data received.
    
    """
    
    # Create a numpy array with the data received.
    a = np.array(mag_data)
    
    # Sort the data only by JD time.
    na = a[a[:,JD_TIME_CE_CALC_DATA].argsort()]
    
    # Extract the columns necessary to calculate the linear regression.
    inst_mag = na[:,INST_MAG_CE_CALC_DATA]
    std_mag = na[:,STD_MAG_CE_CALC_DATA]
    airmass = na[:,AIRMASS_CE_CALC_DATA]
    
    # Subtract these columns to get the y.
    y = inst_mag.astype(np.float) - std_mag.astype(np.float)
    
    # The calculation is:
    # Minst = m + K * airmass
    # Where K is the regression coefficient
    slope, intercept, r_value, p_value, std_err = \
        stats.linregress(airmass.astype(np.float), y)
    
    logging.info("Linear regression for day: " + str(a[0][DAY_CE_CALC_DATA]) +
                 " slope: " + str(slope) + " intercept: " + str(intercept) + \
                 " r-value: " + str(r_value) + " p-value: " + str(p_value) + \
                 " std_err: " + str(std_err))
    
    return slope, intercept

def valid_data_to_calculate_ext_cof(obj_data_for_ext_coef):
    """
    This function examines the data from an object to ensure are coherent,
    i.e., airmass and instrumental magnitude are proportional, greater airmass
    is also a greater magnitude, otherwise these data is not considered valid. 
    
    """
    
    # To know if air mass and magnitude are proportional a linear regression is
    # calculated and the slope inspected. 
    slope, intercept = calculate_extinction_coefficient(obj_data_for_ext_coef)
    
    return slope > 0.0
    
    
def extinction_coefficient(objects, standard_obj_index, \
                           instrumental_magnitudes):
    """
    
    Calculate the atmospheric extinction coefficient using the standard objects.
    
    """
    
    ext_coef = []
    
    # To store all the data necessary to calculate extinction coefficients.
    calc_data_for_ext_coef = []
    
    # To store the different days and filters.
    days = set()
    filters = set()    
    
    # Process each standard object.
    for i in standard_obj_index:
                
        # Retrieve the object data and the instrumental magnitudes measured.
        obj = objects[i]   
        object_inst_mags = instrumental_magnitudes[i]
        
        # Data of an object necessary to calculate extinction coefficients.
        obj_data_for_ext_coef = []
        
        # Process the instrumental magnitudes measured for this object.
        for inst_mag in object_inst_mags:
            # For each object the magnitudes are grouped in different lists.
            for im in inst_mag:

                day = get_day_of_measurement(im[JD_TIME_COL])
                
                days.add(day)
                
                std_mag = get_standard_magnitude(obj, im[FILTER_COL])
                
                # Check that a standard magnitude has been found for
                # this object and filter.
                if std_mag != None:
                    # Also check that there is a valid
                    # instrumental magnitude value.
                    # It is a different 'if' to log a proper message.
                    if im[INST_MAG_COL] != INDEF_VALUE :
                
                        filters.add(im[FILTER_COL])
                        
                        obj_data_for_ext_coef.append([day,
                                                      im[JD_TIME_COL],
                                                      im[INST_MAG_COL],
                                                      std_mag,
                                                      im[AIRMASS_COL],
                                                      im[FILTER_COL],
                                                      obj[OBJ_NAME_COL]])
                    else:
                        logging.info("Standard magnitude undefined for object " + \
                                     obj[OBJ_NAME_COL])
                else:
                    logging.info("Standard magnitude not found for object " + \
                                 obj[OBJ_NAME_COL] + " in filter " + im[FILTER_COL])
        
        # The data for this object is analyzed to check its validity to 
        # calculate the extinction coefficients.
        for d in days:            
            data_subset = [m for m in obj_data_for_ext_coef \
                           if m[DAY_CE_CALC_DATA] == d]
            
            # Check if there is data of this object for this day.
            if len(data_subset) > 0:            
                if valid_data_to_calculate_ext_cof(data_subset) == True:
                    calc_data_for_ext_coef.append(data_subset)
                else:
                    logging.warning("Data to calculate extinction coefficient discarded from object " +
                                    obj[OBJ_NAME_COL] + " for day " + str(d))
    
    if len(calc_data_for_ext_coef) > 0:
        for d in days:
            for f in filters:
                mag = [m for m in calc_data_for_ext_coef \
                       if m[DAY_CE_CALC_DATA] == d and m[FILTER_CE_CALC_DATA] == f]
                
                # Check if there is data of this object for this day.
                if len(mag) > 0:
                    slope, intercept = calculate_extinction_coefficient(mag)
            
                    ext_coef.append([d, f, slope, intercept])
    else:
        logging.warning("There is not enough data to calculate extinction coefficients")
        
    return ext_coef, days, filters

def get_extinction_coefficient(ext_coef, day, filter):
    """
    
    Returns the parameters related to a extinction coefficient
    for a day and filter.
    
    """
    
    # Default values that don't change the returns the instrumental
    # magnitude for the extinction corrected magnitude.
    slope = 1.0
    intercept = 0.0
    
    ec = [e for e in ext_coef \
                   if e[DAY_CE_DATA] == day and e[FILTER_CE_DATA] == filter]
                   
    # Maybe for the filter indicated has not been calculated an
    # extinction coefficient.
    if ec != None and len(ec) > 0:
        slope = ec[0][SLOPE_CE_DATA]
        intercept = ec[0][INTERCEPT_CE_DATA]
    
    return slope, intercept 
        
def get_indexes_of_std_and_no_std(objects, instrumental_magnitudes):
    """
    
    This function returns the indexes for the standard and no standard
    objects.
    Also store to a text file the instrumental magnitudes.
    
    """
    
    standard_obj_index = []
    no_standard_obj_index = []
    
    # For each object. The two list received contains the same 
    # number of objects.
    for i in range(len(objects)):
        
        # Save instrumental magnitudes to a file.
        save_magnitudes(objects[i][OBJ_NAME_COL], INST_MAG_SUFFIX, instrumental_magnitudes[i])        
        
        # Check if it is a standard object to put the object in
        # the right list.
        if objects[i][OBJ_STANDARD_COL] == STANDARD_VALUE:
            standard_obj_index.extend([i])
        else:
            no_standard_obj_index.extend([i])     
            
    
    return standard_obj_index, no_standard_obj_index 

def get_extinction_corrected_mag(obj, \
                                 object_inst_mags, \
                                 ext_coef):
    """
    
    Get the extinction corrected magnitude for the measures
    of the object received. 
    The extinction coefficients are applied and the magnitudes 
    calculated are saved to a file and returned.
    
    """
    
    magnitudes = []
    
    # Process the instrumental magnitudes measured for this object.
    for inst_mag in object_inst_mags:
        # For each object the magnitudes are grouped in different lists.
        for im in inst_mag:
            
            # Check if the instrumental magnitude is defined.
            if im[INST_MAG_COL] != INDEF_VALUE :
            
                # Find the coefficients by day and filter.
                day = get_day_of_measurement(im[JD_TIME_COL])
                filter = im[FILTER_COL]
                
                slope, intercept = \
                    get_extinction_coefficient(ext_coef, day, filter)
                
                # Calculate the extinction corrected magnitude.
                # Mo = Minst - intercept - slope * airmass
                calc_mag = float(im[INST_MAG_COL]) - intercept - \
                    slope * float(im[AIRMASS_COL])
                    
                magnitudes.append([im[JD_TIME_COL], day, calc_mag, \
                                   im[INST_MAG_COL], filter])
            else:
                logging.info("Found an instrumental magnitude undefined for object " + \
                             obj[OBJ_NAME_COL])
            
    # Save extinction corrected magnitude for current object.
    save_magnitudes(obj[OBJ_NAME_COL], CORR_MAG_SUFFIX, [magnitudes])  
    
    return magnitudes      

def calculate_transforming_coefficients(B_V_observed_mag, \
                                        V_observed_mag, 
                                        B_V_std_mag, 
                                        V_std_mag):
    """
    
    Calculate the transforming coefficients.
    
    """   
    
    # First calculation is:
    # Vstd - V0 = slope * (B-V)std + intercept
    y = np.array(V_std_mag).astype(np.float) - \
        np.array(V_observed_mag).astype(np.float)
    
    slope1, intercept1, r_value1, p_value1, std_err1 = \
        stats.linregress(np.array(B_V_std_mag), y)
        
    # Second calculation is:
    # (B-V)std = slope * (B-V)obs + intercept
    
    slope2, intercept2, r_value2, p_value2, std_err2 = \
        stats.linregress(B_V_observed_mag, B_V_std_mag)      
    
    return slope1, intercept1, slope2, intercept2

def get_transforming_coefficients(objects, \
                                  standard_obj_index, \
                                  ext_corr_mags, days, filters):
    """
    
    From the extinction corrected magnitudes of standard object 
    get the transforming coefficients used to calculate the
    calibrated magnitudes.
    
    """  
    
    trans_coef = []
    
    # Put all the sublists corresponding to magnitudes of different object
    # in a list with only a level that contains all the magnitudes.
    magnitudes = [item for sublist in ext_corr_mags for item in sublist]  
    
    # Calculate the coefficients by day.
    for d in days:
        
        # To store the magnitudes for a day.
        B_V_mags_of_day = []
        V_mags_of_day = []
        
        B_V_std_mags_of_objects = []
        V_std_mags_of_objects = []        
        
        # Get filter magnitudes for each object.
        for i in range(len(standard_obj_index)):
            
            object_index = standard_obj_index[i]
            
            # Get the list of corrected magnitudes for this object. 
            obj_mags = ext_corr_mags[i]
            
            # To store the magnitudes for this object in each filter.
            mags_of_B_filter = [m for m in obj_mags \
                       if m[DAY_CEM_COL] == d and \
                       m[FILTER_CEM_COL] == B_FILTER_NAME]
            
            mags_of_V_filter = [m for m in obj_mags \
                       if m[DAY_CEM_COL] == d and \
                       m[FILTER_CEM_COL] == V_FILTER_NAME]           
            
            # If this object has measurements for all the filters.
            # Is is assumed that measurements for each filter are well paired.
            if len(mags_of_B_filter) > 0 and len(mags_of_V_filter) > 0 and \
                len(mags_of_B_filter) == len(mags_of_V_filter):
                
                B_mags_of_obj = np.array(mags_of_B_filter)[:,CE_MAG_CEM_COL]
                V_mags_of_obj = np.array(mags_of_V_filter)[:,CE_MAG_CEM_COL] 
                
                B_mags = B_mags_of_obj.astype(np.float)
                V_mags = V_mags_of_obj.astype(np.float)
            
                # Compute the mean for the magnitudes of this object
                # in each filter. 
                B_mean = np.mean(B_mags)
                V_mean = np.mean(V_mags)

                # Store the mean values of the magnitude observed for
                # these objects to compute the transforming coefficients 
                # of this day.
                B_V_mags_of_day.extend([B_mean - V_mean])
                V_mags_of_day.extend([V_mean])
                
                # Add the standard magnitudes of the object.
                B_std_mag_object = float(objects[object_index][OBJ_B_MAG_COL])
                V_std_mag_object = float(objects[object_index][OBJ_V_MAG_COL])
                
                B_V_std_mags_of_objects.extend([B_std_mag_object - V_std_mag_object])
                V_std_mags_of_objects.extend([V_std_mag_object])
            else:
                logging.info("There is not measurements in all filters for object: " + \
                             objects[object_index][OBJ_NAME_COL] + " at day " + str(d))

        # The coefficients are calculated only if there is twice at least,
        # (any list could be used for this check).
        if len(V_mags_of_day) > 1:
            # Calculate the transforming coefficients of this day using the
            # magnitudes found for this day.   
            c1, c2, c3, c4 = \
                calculate_transforming_coefficients(B_V_mags_of_day, \
                                                    V_mags_of_day, \
                                                    B_V_std_mags_of_objects, \
                                                    V_std_mags_of_objects)
                
            trans_coef.append([d, c1, c2, c3, c4])          
        else:
            logging.warning("No transforming coefficients could be " + 
                            "calculated for day (there is only one " +
                            "standard object) " + str(d))
            
    return trans_coef
    
def calibrated_magnitudes(objects, obj_indexes, ext_corr_mags, trans_coef):
    """
    
    Using the transformation coefficients calculate the calibrated
    magnitudes from the extinction corrected magnitudes and save them
    to a file.
    
    """    
        
    # Calculate for each object.
    for i in obj_indexes:
        
        # Only for those days with coefficients calculated.
        for tc in trans_coef:
            
            # Get the day of current transformation coefficient.
            day = tc[DAY_TRANS_COEF_COL]
            # Get also the coefficients.
            c1 = tc[C1_TRANS_COEF_COL]
            c2 = tc[C2_TRANS_COEF_COL]
            c3 = tc[C3_TRANS_COEF_COL]
            c4 = tc[C4_TRANS_COEF_COL]
            
            # Magnitudes of the object
            obj_mags = ext_corr_mags[i]
            
            # Data for this object.
            obj = objects[obj_indexes[i]]
            
            # To store the magnitudes for this object in each filter.
            mags_of_B_filter = [m for m in obj_mags \
                       if m[DAY_CEM_COL] == day and \
                       m[FILTER_CEM_COL] == B_FILTER_NAME]
            
            mags_of_V_filter = [m for m in obj_mags \
                       if m[DAY_CEM_COL] == day and \
                       m[FILTER_CEM_COL] == V_FILTER_NAME]    
            
            cal_magnitudes = []
            
            # If this object has measurements for all the filters.
            # Is is assumed that measurements for each filter are well paired.
            if len(mags_of_B_filter) > 0 and len(mags_of_V_filter) > 0 and \
                len(mags_of_B_filter) == len(mags_of_V_filter):
                
                B_mags_of_obj = np.array(mags_of_B_filter)[:,CE_MAG_CEM_COL]
                V_mags_of_obj = np.array(mags_of_V_filter)[:,CE_MAG_CEM_COL]
                
                B_obs_mags = B_mags_of_obj.astype(np.float)
                V_obs_mags = V_mags_of_obj.astype(np.float) 
                B_V_obs_mags = B_obs_mags - V_obs_mags
                
                # Calculate the calibrated magnitudes.
                B_V_cal_mag = c3 * B_V_obs_mags + c4
                V_cal_mag = V_obs_mags + c1 * B_V_cal_mag + c2
                
                B_cal_mag = B_V_cal_mag + V_cal_mag
                
                # First the B magnitudes of the object.
                for j in range(len(mags_of_B_filter)):
                    om = mags_of_B_filter[j]
                    
                    cal_magnitudes.append([om[JD_TIME_CEM_COL], \
                                          B_cal_mag[j], \
                                          om[CE_MAG_CEM_COL], \
                                          om[INST_MAG_CEM_COL], \
                                          om[FILTER_CEM_COL]])

                for j in range(len(mags_of_V_filter)):
                    om = mags_of_V_filter[j]
                    
                    cal_magnitudes.append([om[JD_TIME_CEM_COL], \
                                          V_cal_mag[j], \
                                          om[CE_MAG_CEM_COL], \
                                          om[INST_MAG_CEM_COL], \
                                          om[FILTER_CEM_COL]])
                
                # Save the calibrated magnitudes to a file.
                save_magnitudes(obj[OBJ_NAME_COL], CAL_MAG_SUFFIX, [cal_magnitudes])
            else:
                logging.info("Calibrated magnitudes are not calculated for object: " + \
                             obj[OBJ_NAME_COL] + " at day " + str(day) + \
                             ", object magnitudes not available for all the filters.")                

def calculate_calibrated_mag(objects, \
                             standard_obj_index, \
                             no_standard_obj_index, \
                             instrumental_magnitudes, \
                             ext_coef, days, filters):
    """
    
    Calculate the calibrated magnitude of the objects 
    using the extinction coefficient calculated previously and
    calibrating with the standard magnitudes.
    
    """
    
    # To store extinction corrected magnitudes of all objects.
    ext_corr_mags = []
    
    # Calculate the extinction corrected magnitudes of standard objects.
    for i in standard_obj_index:
        obj_mags = get_extinction_corrected_mag(objects[i], \
                                                instrumental_magnitudes[i], \
                                                ext_coef)
        ext_corr_mags.append(obj_mags)
        
    # Calculate from extinction corrected magnitudes of no standard objects
    # the transformation coefficients to calculate the calibrated magnitudes.
    trans_coef = get_transforming_coefficients(objects, \
                                               standard_obj_index, \
                                               ext_corr_mags, \
                                               days, filters)
                       
    # Calculate the extinction corrected magnitudes of no standard objects.
    for i in no_standard_obj_index:
        obj_mags = get_extinction_corrected_mag(objects[i], \
                                                instrumental_magnitudes[i], \
                                                ext_coef)   
        
        ext_corr_mags.append(obj_mags) 
        
    # Build an index that follows the order of the magnitudes inserted.
    obj_indexes = standard_obj_index
    obj_indexes.extend(no_standard_obj_index)
        
    # Calculate the calibrated magnitudes for all the objects.
    calibrated_magnitudes(objects, obj_indexes, ext_corr_mags, trans_coef)

def process_instrumental_magnitudes(objects, instrumental_magnitudes):
    """
    
    This function process the instrumental magnitudes to get magnitudes
    calibrated.
    
    """
    
    standard_obj_index, no_standard_obj_index = \
        get_indexes_of_std_and_no_std(objects, instrumental_magnitudes)                      
            
    ext_coef, days, filters = \
        extinction_coefficient(objects, standard_obj_index, \
                               instrumental_magnitudes)   
    
    # Calculate extinction corrected magnitudes for objects.
    calculate_calibrated_mag(objects, \
                             standard_obj_index, \
                             no_standard_obj_index, \
                             instrumental_magnitudes, \
                             ext_coef, days, filters) 
                                       
def calculate_magnitudes(progargs):
    """ 

    Get the magnitudes of the objects grouping the magnitudes and
    performing the necessary corrections and calibrations.

    """
    
    # Read the list of objects whose magnitudes are needed.
    objects = read_objects_of_interest(progargs)
    
    instrumental_magnitudes = compile_instrumental_magnitudes(objects)
    
    process_instrumental_magnitudes(objects, instrumental_magnitudes)