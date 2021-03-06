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

""" This module read the magnitude files generated by Iraf phot command related
to the stars of interest and compile all then in files with csv format.

Also the extinction corrected magnitudes and calibrated ones calculated from
the instrumental magnitudes are also stored.

"""

import os
from textfiles import *
from constants import *
from starcat import *
from utility import get_day_from_mjd

class Magnitude(object):
    """ Stores a instrumental magnitude and the associated values."""
    
    def __init__(self, star_name, mjd, filter, mag, mag_error, airmass):
        self._star_name = star_name
        self._mjd = mjd
        self._day = mjd
        self._filter = filter
        self._mag = mag
        self._mag_error = mag_error          
        self._airmass = airmass
        # Used when calculating extinction coefficient.
        self._std_mag = None
        # Extinction corrected magnitude.
        self._ext_cor_mag = None
        # Calibrated magnitude.
        self._calib_mag = None 
        
    def __str__(self):
        return "%s %s %s %s %s %s" % \
            (self._star_name, self._mjd, self._filter, \
             self._mag, self._mag_error, self._airmass)
        
    @property
    def star_name(self):
        return self._star_name
        
    @property
    def mjd(self):
        return self._mjd    
    
    @property
    def day(self):
        return self._day      
    
    @day.setter
    def day(self, day):
        self._day = day
            
    @property
    def filter(self):
        return self._filter   
    
    @property
    def mag(self):
        return self._mag    
    
    @property
    def mag_error(self):
        return self._mag_error 
        
    @property
    def airmass(self):
        return self._airmass  
    
    @property  
    def std_mag(self):
        return self._std_mag
    
    @std_mag.setter
    def std_mag(self, mag):
        self._std_mag = mag
        
    @property  
    def ext_cor_mag(self):
        return self._ext_cor_mag
    
    @ext_cor_mag.setter
    def ext_cor_mag(self, ext_cor_mag):
        self._ext_cor_mag = ext_cor_mag
        
    @property  
    def calib_mag(self):
        return self._calib_mag
    
    @calib_mag.setter
    def calib_mag(self, calib_mag):
        self._calib_mag = calib_mag                

class StarMagnitudes(object):
    """ Read and stores the values of the magnitudes of stars."""
    
    # Identifier for star of interest in the coordinates list of a field.
    OBJ_OF_INTEREST_ID = 0
    
    # Number of the column that contains the magnitude value.
    CSV_ID_COOR_COL = 0
    CSV_X_COOR_COL = 1
    CSV_Y_COOR_COL = 2
    CSV_TIME_COL = 3 
    CSV_MAG_COL = 4
    CSV_AIRMASS_COL = 5
    CSV_ERROR_COL = 6
    
    def __init__(self, stars):
        """Constructor.
        
        Args:
            stars: The stars whose magnitudes are read.
            
        """
        
        self._stars = stars
        
        # To store the instrumental magnitudes of the star of interest.
        self._magnitudes = []
        
        # To store the magnitudes of the star of interest and the stars of 
        # reference.
        self._all_magnitudes = [] 
        
        self._star_names = []   
       
        # For each star add a list in each list to contain the data of the star.
        for s in stars:
            self._star_names.append(s.name)
            
            self._magnitudes.append([])
            self._all_magnitudes.append([])
            
        # Sets of filters and days of the magnitudes.
        self._filter = set()
        self._day = set()   
        
    @property  
    def stars(self):
        return self._stars
    
    @property
    def std_stars(self):
        return [s for s in self._stars if s.is_std]
    
    @property
    def no_std_stars(self):
        return [s for s in self._stars if not s.is_std]    
        
    @property
    def days(self):
        return self._day
    
    @property
    def filters(self):
        return self._filter  
    
    def get_std_mag(self, name, filter):      
        std_mag = None
                
        for s in self._stars:
            if s.name == name:
                std_mag = s.get_std_mag(filter)
                
        return std_mag
                
    def get_star_name_from_file_name(self, mag_file):
        """ Get the name of the star contained in the file name.
        
        Args:
            mag_file: Magnitude file where to extract the star name. 
        
        Returns:
            The name of the star.
        
        """
        
        # From the file name get the name of the star.
        star_name_with_path = mag_file[0:mag_file.find(DATANAME_CHAR_SEP)]
         
        return os.path.basename(star_name_with_path)
                

    def get_catalog_file_name(self, mag_file):
        """Get the catalog file name from the magnitude.csv file name.
        
        Args:
            mag_file: Name of the magnitude csv file.
        """
        
        mag_csv_pattern = "%s%s" % \
            (DATA_FINAL_SUFFIX, MAG_CSV_PATTERN)
            
        cat_pattern = ".%s" % (CATALOG_FILE_EXT)
        
        # Get the name of the catalog file from the current CSV file.
        catalog_file_name = mag_file.replace(mag_csv_pattern, cat_pattern)

        return catalog_file_name

    def get_filter_name(self, path):
        """ The name of the directory that contains the file is the name of 
        the filter
        
        """
        
        path_head, filter_name = os.path.split(path)
        
        return filter_name
    
    def get_mags_of_star(self, star_name):
        """Returns the magnitudes of the star name received
        
        Args:
            star_name: Name of the star whose magnitudes are requested.
            
        Returns:
            The magnitudes of the star if available.
        """
        
        mag = None
        
        i = 0
        
        for sn in self._star_names:
            if sn == star_name:
                mag = self._magnitudes[i]
                break
            i = i + 1
                        
        return mag    

    def add_all_mags(self, star_name, star_index, magnitudes, time, filter):
        """Add all the magnitudes sorted by id.
        
        Args:
            stgar_name: Name of the star.
            star_index: Index used to add these magnitudes.
            magnitudes: The magnitudes with the x,y coordinate and the error.
            time: The time of the measurement.
            filter: The filter used for these measurements. 
        
        Returns:        
            A row with the magnitudes sorted and completed with INDEF.    
        
        """
        
        # The row to return. Time and filter to the beginning of the row.
        mag_row = [time, filter]
        
        n_mag = 0
        
        star = self._stars.get_star(star_name)
        
        # Check that the star has been found and it is a no standard one.
        if star is not None and not star.is_std:
        
            # For each star of the field a magnitude is added to the row, 
            # if the magnitude does not exists, INDEF values are added.
            for sf in star.field_stars:
               
                # Get current magnitude to process.
                current_mag = magnitudes[n_mag]
                
                mag_row.extend([current_mag[MAG_COL], \
                                current_mag[MAG_ERR_COL]])
                
                # Next magnitude if there is more magnitude values.
                if n_mag < len(magnitudes) - 1:
                    n_mag += 1                    
            
        self._all_magnitudes[star_index].append(mag_row)

    def read_mag_file(self, mag_file, filter_name, star_name, star_catalog):
        """Read the magnitudes from the file.
        
        Args:
            mag_file: The name of the file to read.
            filter_name: Name of the filter for these magnitudes.
            star_name: Name of the star whose magnitudes are read.
            star_catalog: Catalog of X, Y coordinates of the stars in the image. 
        
        """
        
        logging.debug("Processing magnitudes file: " + mag_file)
        
        try:            
            with open(mag_file, 'rb') as fr:
                reader = csv.reader(fr)
                nrow = 0
                mag = []
                all_mag = []
                mjd = None
                
                # Process all the instrumental magnitudes in the file.
                for row in reader:
                    # Get a list of values from the CSV row read.
                    fields = str(row).translate(None, "[]\'").split()                            
                    
                    # Check that MJD has a defined value.
                    if fields[self.CSV_TIME_COL] != INDEF_VALUE:                
                        
                        # Save the mjd, it is the same for all the rows.
                        mjd = fields[self.CSV_TIME_COL]    
                        
                        day = get_day_from_mjd(mjd)  
                        
                        # Add day and filter.
                        self._day.add(day)
                        self._filter.add(filter_name)  
                        
                        try:
                            current_coor_id = star_catalog.id(nrow)
                            
                            # If it is the star of interest, add the magnitude to
                            # the magnitudes list.
                            if nrow == 0:                                
                                im = Magnitude(
                                        star_name,
                                        mjd,
                                        filter_name,
                                        fields[StarMagnitudes.CSV_MAG_COL],
                                        fields[StarMagnitudes.CSV_ERROR_COL],
                                        fields[StarMagnitudes.CSV_AIRMASS_COL])
                                
                                im.day = day
                                
                                mag.append(im)   
                                
                            # Add the magnitude to the all magnitudes list.
                            all_mag.append([fields[StarMagnitudes.CSV_MAG_COL],
                                            fields[StarMagnitudes.CSV_ERROR_COL],
                                            current_coor_id])                                
                                                         
                        except StarCatalogException as sce:
                            logging.error(sce)               
                        
                        nrow += 1
                    else:
                        logging.warning("Found INDEF value for the observation " + 
                                        "in file: '%s'" % (mag_file))
                
                star_index = self._stars.get_star_index(star_name)       
                
                if star_index >= 0: 
                    self._magnitudes[star_index].extend(mag)
    
                    if len(all_mag) > 0:
                        # Add all the magnitudes in the image sorted by 
                        # identifier.
                        self.add_all_mags(star_name, star_index, \
                                          all_mag, mjd, filter_name)                
                    
                logging.info("Processed instrumental magnitudes of %d stars." % 
                             (nrow))
        except IOError as ioe:
            logging.error("Reading magnitudes file: '%s'" % (mag_file))                 

    def read_inst_magnitudes(self, mag_file, path):
        """Searches in a given path all the magnitudes files.
        
        Args:
            mag_file: File where to look for the magnitudes.
            path: Path where to search the files.
        
        """         
        
        # Filter for the magnitudes of this file.
        filter_name = self.get_filter_name(path)
        
        # Get the name of the star related to this file.
        star_name = self.get_star_name_from_file_name(mag_file)          
            
        catalog_file_name = self.get_catalog_file_name(mag_file)
        
        # Search the catalog file containing the x,y coordinates of each star.
        if os.path.exists(catalog_file_name):
            
            try:            
                star_catalog = StarCatalog(catalog_file_name)
        
                # Coordinates used to calculate the magnitudes of the image.
                star_catalog.read()
                
                self.read_mag_file(mag_file, filter_name, star_name, 
                                   star_catalog)
                
            except StarCatalogException as sce:
                    logging.error(sce) 
    
    def save_all_mag(self, target_dir):
        """ Save the magnitudes received.
        
        Args:
            target_dir: The directory for results.
        
        """
        
        # For each star. The two list received contains the same 
        # number of stars.
        i = 0
        for s in self._stars:
            # Save only no standard stars.
            if not s.is_std:
                # Check not empty.
                if self._all_magnitudes[i]:                    
                    # Get the name of the output file.
                    output_file_name = "%s%s%s%s" % \
                        (s.name, ALL_INST_MAG_SUFFIX, ".", TSV_FILE_EXT)
                        
                    output_full_path = os.path.join(target_dir, 
                                                    output_file_name)
                        
                    try:                
                        with open(output_full_path, 'w') as fw:
                            
                            writer = csv.writer(fw, delimiter='\t')
                    
                            # It is a list that contains sublists, each sublist is
                            # a different magnitude, so each one is written as a row.
                            for imag in self._all_magnitudes[i]:
                            
                                # Write each magnitude in a row.
                                writer.writerow(imag)   
                                
                    except IOError as ioe:
                        logging.error("Writing magnitudes file: '%s'" % 
                                      (output_full_path)) 
            
            i = i + 1    
            
    def save_magnitudes(self, target_dir):
        """Save the magnitudes to a text file.
        
        Args:     
            target_dir: The directory for results.
        
        """
        
        # For each star. The two list received contains the same 
        # number of stars.
        i = 0
        for s in self._stars:    
            # Retrieve the magnitudes of current star.
            mags = self._magnitudes[i]
            
            # Check not empty.
            if mags:                
                          
                # Get the name of the output file.
                output_file_name = "%s%s%s" % (s.name, ".", TSV_FILE_EXT)  
                
                output_full_path = os.path.join(target_dir, output_file_name)                    
                    
                try:              
                    with open(output_full_path, 'w') as fw:
                        
                        writer = csv.writer(fw, delimiter='\t')
    
                        # It is a list that contains sublists, each sublist is
                        # a different magnitude, so each one is written as a row.
                        for m in mags:
                            
                            m_to_row = [m.mjd, m.filter, m.airmass, \
                                        m.mag, m.mag_error, \
                                        m.ext_cor_mag, m.calib_mag]                  
                        
                            # Write each magnitude in a row.
                            writer.writerow(m_to_row)
                            
                except IOError as ioe:
                    logging.error("Writing magnitudes file: '%s'" % 
                                  (output_full_path))                             
            i += 1
            
    def read_magnitude_files(self, target_dir):
        """Look for files that contain magnitudes and process them in current 
        directory adding the magnitudes to each star.
        
        Args:
            target_dir: Directories to search for magnitude files.
        
        """       
    
        # Get the list of files related to magnitudes ignoring hidden files 
        # (starting with dot).
        mag_files_full_path = \
            [f for f in glob.glob(os.path.join(target_dir, 
                                               "*.%s" % (TSV_FILE_EXT))) \
            if not os.path.basename(f).startswith('.')]
            
        logging.debug("Found %d files with magnitudes." %
                      (len(mag_files_full_path))) 
        
        # Process the files related to magnitudes.
        for mag_file in mag_files_full_path:
            
            star_name = mag_file[:mag_file.find('.')]
            
            star = self._stars.get_star(star_name)
            
            if star is not None:
                
                try:
                    logging.debug("Reading magnitude file '%s'." % 
                                  (mag_file))
                    
                    mag_list = []
                    
                    with open(mag_file, 'rb') as fr:
                        reader = csv.reader(fr, delimiter='\t')        
                        
                        # Each line contains data for a magnitude of this star.
                        for row in reader:
                            
                            # At least the number of values for the 
                            # instrumental magnitude.
                            if len(row) >= 5:                 
                                mag = Magnitude(star_name,
                                                row[0], # mjd
                                                row[1], # filter
                                                row[3], # mag
                                                row[4], # mag_error
                                                row[2]) # airmass
                                                                
                                # It also has the extinction corrected magnitude.
                                if len(row) == 6: 
                                    mag.ext_cor_mag = row[5]
                                    
                                # It also has the calibrated magnitude.
                                if len(row) == 7:  
                                    mag.calib_mag = row[6]
                                    
                                mag_list.append(mag)
                       
                    # Add the magnitudes to the appropriate star.
                    star_index = self._star_names.index(star_name)       
            
                    if star_index >= 0:                 
                        self._magnitudes[star_index].extend(mag_list)         
                                                                                                                                   
                except IOError as ioe:
                    logging.error("Reading the file of magnitudes: '%s'." % 
                                  (mag_file))    
            else:
                logging.warning("Magnitude file '%s' corresponds to an unknown star %s." %
                                (mag_file, star_name))                                