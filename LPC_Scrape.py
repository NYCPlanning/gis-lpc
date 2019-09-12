# Utilizes Python 2, but requires that the requests library is installed in the appropriate default Python2 installation
# path. If this custom Python distribution is not available and it is not possible to install the requests library
# must utilize version of Python 3 with requests library (ArcGIS Pro Python installation has this library)

import requests, arcpy, ConfigParser, traceback, sys, os, zipfile, datetime, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

try:
    # Set configuration file path
    config = ConfigParser.ConfigParser()
    config.read(r'LPC_Scrape_template.ini')

    # Set log path
    log_path = config.get("PATHS", "log_path")
    log = open(log_path, "a")

    # Set start time
    StartTime = datetime.datetime.now().replace(microsecond=0)

    # Set variable for today's date
    today = datetime.datetime.today()
    today = datetime.datetime.strftime(today, '%b %d %Y')

    # Set translator paths
    print("Setting arcdir")
    Arcdir = arcpy.GetInstallInfo("desktop")["InstallDir"]
    translator = Arcdir + "Metadata/Translator/ARCGIS2FGDC.xml"
    remove_geoprocess_xslt = Arcdir + "Metadata/Stylesheets/gpTools/remove geoprocessing history.xslt"
    remove_lcl_storage_xslt = Arcdir + "Metadata/Stylesheets/gpTools/remove local storage info.xslt"
    print("Arcdir set")

    # Set variable paths
    print("Setting variable paths")
    sde_path = config.get('PATHS', 'sde_path')
    lpc_temp_path = config.get('PATHS', 'temp_dir_path')
    building_lots_lyr_path = config.get('PATHS', 'building_lots_lyr_path')
    facilities_landmarks_lyr_path = config.get('PATHS', 'facilities_landmarks_lyr_path')
    boundaries_zoning_related_lyr_path = config.get('PATHS', 'boundaries_zoning_related_lyr_path')
    print("Variable paths set")

    # Disconnect all users
    arcpy.AcceptConnections(sde_path, False)
    arcpy.DisconnectUser(sde_path, "ALL")

    # Create temp directory if it doesn't already exist
    print("Creating temporary directory")
    if not os.path.exists(lpc_temp_path):
        os.mkdir(lpc_temp_path)
    print("Temporary directory created")

    # Set proxy credential information
    proxies = {
        'http': config.get('PROXIES', 'http_proxy'),
        'https': config.get('PROXIES', 'https_proxy')
    }

    # Scrape update dates from item description due to lack of publication date in metadata

    def extract_update(config_url_tag):
        # Establish connection to Open Data platform
        print("Establishing connection to ")
        r = requests.get(config.get('UPDATE_URLS', config_url_tag),
                         proxies=proxies,
                         allow_redirects=True,
                         verify=False)
        c = r.content
        soup = BeautifulSoup(c, 'html.parser')
        update_date = soup.find('span', 'aboutUpdateDate').getText()
        return(update_date)

    # Assign date variables for updating metadata content and publication information

    hist_dist_update = extract_update('historic_dist_url')
    hist_dist_update_dt = datetime.datetime.strptime(hist_dist_update, '%b %d %Y')
    hist_dist_update_str = datetime.datetime.strftime(hist_dist_update_dt, '%Y%m%d')
    print(hist_dist_update, hist_dist_update_dt, hist_dist_update_str)
    indiv_landmark_update = extract_update('indiv_landmarks_url')
    indiv_landmark_update_dt = datetime.datetime.strptime(indiv_landmark_update, '%b %d %Y')
    indiv_landmark_update_str = datetime.datetime.strftime(indiv_landmark_update_dt, '%Y%m%d')
    print(indiv_landmark_update, indiv_landmark_update_dt, indiv_landmark_update_str)
    scenic_landmark_update = extract_update('scenic_landmarks_url')
    scenic_landmark_update_dt = datetime.datetime.strptime(scenic_landmark_update, '%b %d %Y')
    scenic_landmark_update_str = datetime.datetime.strftime(scenic_landmark_update_dt, '%Y%m%d')
    print(scenic_landmark_update, scenic_landmark_update_dt, scenic_landmark_update_str)
    indiv_landmark_hist_dist_db_update = extract_update('indiv_lndmk_hist_dist_db_url')
    indiv_landmark_hist_dist_db_dt = datetime.datetime.strptime(indiv_landmark_hist_dist_db_update, '%b %d %Y')
    indiv_landmark_hist_dist_db_str = datetime.datetime.strftime(indiv_landmark_hist_dist_db_dt, '%Y%m%d')
    print(indiv_landmark_hist_dist_db_update, indiv_landmark_hist_dist_db_dt, indiv_landmark_hist_dist_db_str)

    # Download and extract shapefiles from Open Data platform

    def download_zip(config_url_tag, zip_path):
        # Establish connection to Open Data platform
        r = requests.get(config.get('DOWNLOAD_URLS', config_url_tag),
                         proxies=proxies,
                         allow_redirects=True,
                         verify=False)
        c = r.content
        open(zip_path, 'wb').write(c)

        zip = zipfile.ZipFile(zip_path)

        # Extract zip to C:\temp\building_footprints directory

        print("Extracting zipped LPC files")
        zip.extractall(lpc_temp_path)
        print("Export complete")

    print("Downloading historic districts zip")
    download_zip('historic_dist_url', os.path.join(lpc_temp_path, 'lpc_historic_districts.zip'))
    print("Downloading individual landmarks zip")
    download_zip('indiv_landmarks_url', os.path.join(lpc_temp_path, 'lpc_individual_landmarks.zip'))
    print("Downloading scenic landmarks zip")
    download_zip('scenic_landmarks_url', os.path.join(lpc_temp_path, 'lpc_scenic_landmarks.zip'))
    print("Downloading individual landmark historic districts database")
    download_zip('indiv_lndmk_hist_dist_db_url', os.path.join(lpc_temp_path, 'indiv_lndmk_hist_dist_db.zip'))
    print("All downloads complete")

    arcpy.env.workspace = lpc_temp_path
    arcpy.env.overwriteOutput = True

    # Import previous metadata to newly extracted shapefiles

    for f in os.listdir(lpc_temp_path):
        if f == 'Historic Districts.shp':
            print("Hit - {}".format(f))
            print("Compiling field name list for historic districts")
            hist_field_list = set([field.name for field in arcpy.ListFields(os.path.join(lpc_temp_path, f))])

        if f == 'Landmark_List.shp':
            print("Hit - {}".format(f))
            arcpy.MetadataImporter_conversion(os.path.join(sde_path, 'LPC_Individual_Landmarks'),
                                              os.path.join(lpc_temp_path, f))

            # Create Designated Individual Landmarks from Individual Landmarks dataset
            # Query used - LM_TYPE = Individual Landmark and STATUS = DESIGNATED and MOST_CURRENT = 1

            lm_type = arcpy.AddFieldDelimiters(os.path.join(sde_path, f), 'LM_TYPE')
            status = arcpy.AddFieldDelimiters(os.path.join(sde_path, f), 'STATUS')
            current = arcpy.AddFieldDelimiters(os.path.join(sde_path, f), 'MOST_CURRE')
            designated_expression = """{0} = 'Individual Landmark' AND {1} = 'DESIGNATED' AND {2} = {3}""".format(lm_type, status, current, 1)
            arcpy.FeatureClassToFeatureClass_conversion(os.path.join(lpc_temp_path, f),
                                                        lpc_temp_path,
                                                        'Designated_Landmark_List',
                                                        designated_expression)
            print("Compiling field name list for individual landmarks")
            indiv_landmark_field_list = set([field.name for field in arcpy.ListFields(os.path.join(lpc_temp_path, f))])

        if 'Scenic' in f and f.endswith('.shp'):
            print("Hit - {}".format(f))
            print("Compiling field name list for scenic landmarks")
            scenic_field_list = set([field.name for field in arcpy.ListFields(os.path.join(lpc_temp_path, f))])
        if f == 'IND_HD_Bld_DB.shp':
            print("Hit - {}".format(f))
            print("Compiling field name list for individual historic database")
            ind_hist_db_field_list = set([field.name for field in arcpy.ListFields(os.path.join(lpc_temp_path, f))])

    # Check previous field names against new open data field names

    sde_hist_field_list = set([field.name for field in arcpy.ListFields(os.path.join(sde_path, 'LPC_Historic_Districts'))])
    sde_indiv_landmark_field_list = set([field.name for field in arcpy.ListFields(os.path.join(sde_path, 'LPC_Individual_Landmarks'))])
    sde_scenic_field_list = set([field.name for field in arcpy.ListFields(os.path.join(sde_path, 'LPC_Scenic_Landmarks'))])
    sde_ind_hist_db_field_list = set([field.name for field in arcpy.ListFields(os.path.join(sde_path, 'LPC_Individual_Landmark_Historic_Districts_Building_Database'))])

    expected_fields = ['FID', 'OBJECTID', 'OBJECTID_1', 'Shape.STArea()', 'Shape.STLength()', 'Shape_area', 'Shape_len']

    sde_hist_only = sde_hist_field_list - hist_field_list
    print("In Historic Districts SDE PROD but not Open Data: {}".format(sde_hist_only))
    open_data_hist_only = hist_field_list - sde_hist_field_list
    print("In Historic Districts Open Data but not SDE PROD: {}".format(open_data_hist_only))
    sde_individual_landmarks_only = sde_indiv_landmark_field_list - indiv_landmark_field_list
    print("In Individual Landmarks SDE PROD but not Open Data: {}".format(sde_individual_landmarks_only))
    open_data_individual_landmarks_only = indiv_landmark_field_list - sde_indiv_landmark_field_list
    print("In Individual Landmarks Open Data but not SDE PROD: {}".format(open_data_individual_landmarks_only))
    sde_scenic_landmarks_only = sde_scenic_field_list - scenic_field_list
    print("In Scenic Landmarks SDE PROD but not Open Data: {}".format(sde_scenic_landmarks_only))
    open_data_scenic_landmarks_only = scenic_field_list - sde_scenic_field_list
    print("In Scenic Landmarks Open Data but not SDE PROD: {}".format(open_data_scenic_landmarks_only))
    sde_individual_historic_db_only = sde_ind_hist_db_field_list - ind_hist_db_field_list
    print("In Individual Historic DB SDE PROD but not Open Data: {}".format(sde_individual_historic_db_only))
    open_data_individual_historic_db_only = ind_hist_db_field_list - sde_ind_hist_db_field_list
    print("In Individual Historic DB Open Data but not SDE PROD: {}".format(open_data_individual_historic_db_only))

    # Export shapefiles to SDE PROD

    arcpy.env.workspace = sde_path
    arcpy.env.overwriteOutput = True

    # Define function for updating metadata summary and publication date information and exporting to SDE PROD

    def update_metadata_production_export(sde_name, pub_date_update, pub_date_str, download_date, description_cutoff):
        arcpy.MetadataImporter_conversion(os.path.join(sde_path, sde_name),
                                          os.path.join(lpc_temp_path, f))
        arcpy.XSLTransform_conversion(os.path.join(lpc_temp_path, f.replace('.shp', '.shp.xml')),
                                      remove_lcl_storage_xslt,
                                      os.path.join(lpc_temp_path, '{}_rm_lcl_storage.xml'.format(f.split('.')[0])))
        tree = ET.parse(os.path.join(lpc_temp_path, '{}_rm_lcl_storage.xml'.format(f.split('.')[0])))
        root = tree.getroot()
        for pubdate in root.iter('pubdate'):
            pubdate.text = pub_date_update
        for descrip in root.iter('abstract'):
            descrip.text = descrip.text.replace(descrip.text[-description_cutoff:], 'Dataset last updated: {}. Dataset last downloaded: {}'.format(pub_date_str, download_date))
            tree.write(os.path.join(lpc_temp_path, '{}_update_summary.xml'.format(f.split('.')[0])))
            arcpy.FeatureClassToFeatureClass_conversion(os.path.join(lpc_temp_path, f),
                                                        sde_path, sde_name)
            arcpy.XSLTransform_conversion(os.path.join(lpc_temp_path, '{}_update_summary.xml'.format(f.split('.')[0])),
                                          remove_geoprocess_xslt,
                                          os.path.join(lpc_temp_path, '{}_rm_geoproc_final.xml'.format(f.split('.')[0])))
            arcpy.MetadataImporter_conversion(
                os.path.join(lpc_temp_path, '{}_rm_geoproc_final.xml'.format(f.split('.')[0])),
                os.path.join(sde_path, sde_name)
            )
            arcpy.UpgradeMetadata_conversion(os.path.join(sde_path, sde_name), 'FGDC_TO_ARCGIS')
            arcpy.Delete_management(os.path.join(lpc_temp_path, '{}_rm_lcl_storage.xml'))
            arcpy.Delete_management(os.path.join(lpc_temp_path, '{}_update_summary.xml'))
            arcpy.Delete_management(os.path.join(lpc_temp_path, '{}_rm_geoproc_final.xml'))

    # Updating metadata summary and publication date information and exporting to SDE PROD

    for f in os.listdir(lpc_temp_path):
        if f.endswith('.shp'):
            print("Exporting {} to SDE PROD".format(f))
            if 'Historic Districts' in f:
                update_metadata_production_export('LPC_Historic_Districts',
                                                  hist_dist_update_str,
                                                  hist_dist_update,
                                                  today,
                                                  71)
            if 'Designated_Landmark_List' in f:
                update_metadata_production_export('LPC_Designated_Individual_Landmarks',
                                                  indiv_landmark_update_str,
                                                  indiv_landmark_update,
                                                  today,
                                                  70)
            if 'Landmark_List' in f:
                update_metadata_production_export('LPC_Individual_Landmarks',
                                                  indiv_landmark_update_str,
                                                  indiv_landmark_update,
                                                  today,
                                                  70)
            if 'IND_HD_Bld_DB' in f:
                update_metadata_production_export('LPC_Individual_Landmark_Historic_Districts_Building_Database',
                                                  indiv_landmark_hist_dist_db_str,
                                                  indiv_landmark_hist_dist_db_update,
                                                  today,
                                                  70)
            if 'Scenic' in f:
                update_metadata_production_export('LPC_Scenic_Landmarks',
                                                  scenic_landmark_update_str,
                                                  scenic_landmark_update,
                                                  today,
                                                  71)

    # Export stand-alone xml files to requisite M: drive layer directories

    print("Exporting stand-alone metadata xml files for all requisite M: drive layer files")
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Designated_Individual_Landmarks'), translator,
                                    os.path.join(building_lots_lyr_path, 'Individual Landmarks - Designated (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Individual_Landmark_Historic_Districts_Building_Database'),
                                    translator, os.path.join(building_lots_lyr_path, 'Landmark and Historic District buildings (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Individual_Landmarks'), translator,
                                    os.path.join(building_lots_lyr_path, 'Landmark Actions (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Scenic_Landmarks'), translator,
                                    os.path.join(facilities_landmarks_lyr_path, 'Scenic Landmarks (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Historic_Districts'), translator,
                                    os.path.join(facilities_landmarks_lyr_path, 'Historic Districts (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Historic_Districts'), translator,
                                    os.path.join(facilities_landmarks_lyr_path,
                                                 'Historic Districts - Designated (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Individual_Landmarks'), translator,
                                    os.path.join(facilities_landmarks_lyr_path, 'Landmark Actions (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Designated_Individual_Landmarks'), translator,
                                    os.path.join(facilities_landmarks_lyr_path, 'Individual Landmarks - Designated (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Individual_Landmarks'), translator,
                                    os.path.join(facilities_landmarks_lyr_path, 'Landmark Actions (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Individual_Landmark_Historic_Districts_Building_Database'), translator,
                                    os.path.join(facilities_landmarks_lyr_path, 'Landmark and Historic District buildings (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Historic_Districts'), translator,
                                    os.path.join(boundaries_zoning_related_lyr_path, 'Historic Districts - Designated (LPC).lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Historic_Districts'), translator,
                                    os.path.join(facilities_landmarks_lyr_path, 'Historic Districts.lyr.xml'))
    arcpy.ExportMetadata_conversion(os.path.join(sde_path, 'LPC_Scenic_Landmarks'), translator,
                                    os.path.join(facilities_landmarks_lyr_path, 'Scenic Landmarks (LPC).lyr.xml'))
    print("All stand-alone metadata xml files have been generated for requisite M: drive layer files")

    # Write Start, End, and Total Time to log-file.

    EndTime = datetime.datetime.now().replace(microsecond=0)
    print("Script runtime: {}".format(EndTime - StartTime))

    log.write(str(StartTime) + "\t" + str(EndTime) + "\t" + str(EndTime - StartTime) + "\n")
    log.close()

    # accept connections to GISPROD again
    arcpy.AcceptConnections(sde_path, True)

except:

    # accept connections to GISPROD again
    arcpy.AcceptConnections(sde_path, True)

    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    pymsg = "PYTHON ERRORS:\nTraceback Info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages() + "\n"

    print pymsg
    print msgs

    log.write("" + pymsg + "\n")
    log.write("" + msgs + "")
    log.write("\n")
    log.close()
