# Landmarks Preservation Commission Web Scrape

*******************************

The New York City Landmarks Preservation Commission is the New York City agency charged with administering the city's Landmarks Preservation Law. This script is used to scrape the NYC Open Data platform for the most recent LPC data sets and to update and distribute these data sets accordingly across DCP's internal network file-systems.

### Prerequisites

An installation of Python 2 with the following packages is required. A version of Python with the default ArcPy installation that comes with ArcGIS Desktop is required in order to utilize Metadata functionality that is currently not available in the default ArcPy installation that comes with ArcGIS Pro (Python 3).

##### BuildingFootprints\_Scrape.py

```
requests, arcpy, ConfigParser, traceback, sys, os, zipfile, datetime, xml.etree.ElementTree, BeautifulSoup
```

### Instructions for running

##### LPC\_Scrape.py

1. Open the script in any integrated development environment (PyCharm is suggested)

2. Ensure that your IDE is set to be utilizing a version of Python 2 with the required python packages available. 

3. Ensure that the configuration ini file is up-to-date with path variables. If any paths have changed since the time of this writing, those changes must be reflected in the Config.ini file.

4. Run the script. It will create a temporary directory on the user’s C: drive for storing the downloaded requisite LPC data sets. It will also parse each data set’s Open Data page for the provided update-date. 

5. SDE PROD metadata will be imported into the downloaded shapefiles and altered to update the publication date and description content (for description content, updating publication date of data and download date of data).

6. Update layer files on M: drive by generating new stand-alone xml files for each newly downloaded data set, respectively.

