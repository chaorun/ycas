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
to the objects of interest and compile all then in files with csv format.

"""

from textfiles import *
from constants import *
from utility import get_day_from_mjd

class Magnitude(object):
    """ Stores a instrumental magnitude and the associated values.
    
    """
    
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
    """ Read and stores the values of the magnitudes of stars.
    
    """
    
    # Identifier for object of interest in the coordinates list of a field.
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
        """ Get the name of the object contained in the file name.
        
        Args:
            mag_file: Magnitude file where to extract the star name. 
        
        Returns:
            The name of the star.
        
        """
        
        # From the file name get the name of the object.
        star_name_with_path = mag_file[0:mag_file.find(DATANAME_CHAR_SEP)]
         
        return os.path.basename(star_name_with_path)
                

    def get_catalog_file_name(self, mag_file):
        # Read the catalog file that corresponds to this file.
        # First get the name of the catalog file from the current CSV file.
        catalog_file_name = mag_file.replace(
            DATA_FINAL_SUFFIX + FILE_NAME_PARTS_DELIM + MAGNITUDE_FILE_EXT + 
            "." + CSV_FILE_EXT, 
            "." + CATALOG_FILE_EXT)
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
                
                if int(sf.id) == current_mag[MAG_ID_COL]:
                    # If there is a magnitude for this reference, 
                    # add the magnitude.
                    mag_row.extend([current_mag[MAG_COL], \
                                    current_mag[MAG_ERR_COL]])
                    
                    # Next magnitude if there is more magnitude values.
                    if n_mag < len(magnitudes) - 1:
                        n_mag += 1
                else:
                    # There is no magnitude for this reference, add INDEF values.
                    mag_row.extend([INDEF_VALUE, INDEF_VALUE])                     
            
        self._all_magnitudes[star_index].append(mag_row)

    def read_mag_file(self, mag_file, filter_name, star_name, coordinates):
        """Read the magnitudes from the file.
        
        Args:
            mag_file: The name of the file to read.
            filter_name: Name of the filter for these magnitudes.
            star_name: Name of the star whose magnitudes are read.
            coordinates: List of X, Y coordinates of the stars in the image. 
        
        """
        
        logging.debug("Processing magnitudes file: " + mag_file)
        
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
                    
                    # Get the identifier for current coordinate.
                    current_coor = coordinates[nrow]
                    current_coor_id = int(current_coor[CAT_ID_COL])
                    
                    # If it is the object of interest, add the magnitude to the
                    # magnitudes list.
                    if current_coor_id == StarMagnitudes.OBJ_OF_INTEREST_ID:
                        im = Magnitude(star_name,
                                       mjd,
                                       filter_name,
                                       fields[self.CSV_MAG_COL],
                                       fields[self.CSV_ERROR_COL],
                                       fields[self.CSV_AIRMASS_COL])
                        
                        im.day = day
                        
                        mag.append(im)
                    
                    # Add the magnitude to the all magnitudes list.
                    all_mag.append([fields[self.CSV_MAG_COL], \
                                    fields[self.CSV_ERROR_COL], \
                                    current_coor_id])
                    
                    nrow += 1
                else:
                    logging.warning("Found INDEF value for the observation " + 
                                    "in file %s" % (mag_file))
            
            star_index = self._star_names.index(star_name)       
            
            if star_index >= 0: 
                
                self._magnitudes[star_index].extend(mag)

                if len(all_mag) > 0:
                    # Add all the magnitudes in the image sorted by identifier.
                    self.add_all_mags(star_name, star_index, \
                                      all_mag, mjd, filter_name)                
                
            logging.info("Processed instrumental magnitudes of%d stars." % 
                         (nrow))

    def read_inst_magnitudes(self, mag_file, path):
        """Searches in a given path all the magnitudes files.
        
        Args:
            mag_file: File where to look for the magnitudes.
            path: Path where to search the files.
        
        """         
        
        # Filter for the magnitudes of this file.
        filter_name = self.get_filter_name(path)
        
        # Get the name of the object related to this file.
        star_name = self.get_star_name_from_file_name(mag_file)          
            
        catalog_file_name = self.get_catalog_file_name(mag_file)
        
        # Search the catalog file containing the x,y coordinates of each star.
        if os.path.exists(catalog_file_name):
        
            # List of coordinates used to calculate the magnitudes of the image.
            coordinates = read_catalog_file(catalog_file_name)
            
            self.read_mag_file(mag_file, filter_name, star_name, coordinates)
    
    def save_all_mag(self):
        """ Save the magnitudes received.   
        
        """
        
        # For each object. The two list received contains the same 
        # number of objects.
        i = 0
        for s in self._stars:
            # Save only no standard stars.
            if not s.is_std:
                # Check not empty.
                if self._all_magnitudes[i]:                    
                    # Get the name of the output file.
                    output_file_name = "%s%s%s%s" % \
                        (s.name, ALL_INST_MAG_SUFFIX, ".", TSV_FILE_EXT)
                
                    with open(output_file_name, 'w') as fw:
                        
                        writer = csv.writer(fw, delimiter='\t')
                
                        # It is a list that contains sublists, each sublist is
                        # a different magnitude, so each one is written as a row.
                        for imag in self._all_magnitudes[i]:
                        
                            # Write each magnitude in a row.
                            writer.writerow(imag)                     
            
            i = i + 1    
            
    def save_magnitudes(self):
        """Save the magnitudes to a text file.
        
        Args:     
            star_name: Name of the object that corresponds to the magnitudes.
            magnitudes: List of magnitudes.
        
        """
        
        # For each object. The two list received contains the same 
        # number of objects.
        i = 0
        for s in self._stars:          
            
            # Retrieve the magnitudes of current star.
            mags = self._magnitudes[i]
            
            # Check not empty.
            if mags:                
                          
                # Get the name of the output file.
                output_file_name = "%s%s%s" % (s.name, ".", TSV_FILE_EXT)      
                    
                print output_file_name      
        
                with open(output_file_name, 'w') as fw:
                    
                    writer = csv.writer(fw, delimiter='\t')

                    # It is a list that contains sublists, each sublist is
                    # a different magnitude, so each one is written as a row.
                    for m in mags:
                        
                        m_to_row = [m.mjd, m.filter, m.airmass, \
                                    m.mag, m.mag_error, \
                                    m.ext_cor_mag, m.calib_mag]                  
                    
                        # Write each magnitude in a row.
                        writer.writerow(m_to_row) 
                    
            i = i + 1                   