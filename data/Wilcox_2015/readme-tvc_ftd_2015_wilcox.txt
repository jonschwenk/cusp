This readme-tvc_ftd_2015_wilcox.txt file was generated on 2020-02-05 by Laurier Library Research Data Services <library.wlu.ca>


-------------------
GENERAL INFORMATION
-------------------


1. Dataset Name


Frost table depth with associated snow and landscape variables at Trail Valley Creek, NT, 2015 




2. Author Contact Information


Principal Investigator Contact Information
            Name: Wilcox, Evan J.
           Institution: Wilfrid Laurier University
           Address: Waterloo, Ontario, Canada
           Email: wilc0150@mylaurier.ca


3. Date of data collection (YYYY-MM-DD)
        
2015-06-11 to 2015-08-20


4. Geographic location of data collection (where was data collected?): 


Data was collected at Trail Valley Creek, NT, Canada. Bounding box:
North: 68°44'54.39"N
South  68°44'19.00"N
West: 133°30'2.74"W
East:133°29'6.59"W
 


-----------------------------------
SHARING/ACCESS/CITATION INFORMATION
----------------------------------- 


1. Licenses/restrictions placed on the data:  


This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (http://creativecommons.org/licenses/by-nc-sa/4.0/).


Access, Use, and Distribution of these data, metadata, and associated materials are governed by this CC BY-NC-SA 4.0 license.


The terms of this license are available at: https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode


A plain language summary of CC BY-NS-SA 4.0 is below. It does not replace the license. Under CC BY-NS-SA 4.0, users of this data, metadata, associated materials, but not code and scripts, are free to:


Share — copy and redistribute the material in any medium or format
Adapt — remix, transform, and build upon the material


The CC BY-NC-SA 4.0 license has the following requirements:


Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made. You may do so in any reasonable manner, but not in any way that suggests the licensor endorses you or your use.
NonCommercial — You may not use the material for commercial purposes.
ShareAlike — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.




2. Links to publications that cite or use the data:
        
Wilcox, E. J., Keim, D., de Jong, T., Walker, B., Sonnentag, O., Sniderhan, A.E., Mann, P., Marsh, P. (2019). Tundra shrub expansion may amplify permafrost thaw by advancing snowmelt timing. Arctic Science, 5 (4), 202–217. doi: https://doi.org/10.1139/as-2018-0028
 
3. Recommended citation for the data:

Wilcox, E. J., Keim, D., de Jong, T., Walker, B., Mann, P., Marsh, P. (2020). "Frost table depth with associated snow and landscape variables at Trail Valley Creek, NT, 2015." https://doi.org/10.5683/SP2/9ZGR5U. Scholars Portal Dataverse.



---------------------
DATA & FILE OVERVIEW
---------------------


1. File List


A. Filename: tvc_ftd_2015_wilcox.xls
Tabular Data 113KB.  13 Variables. 1528 Observations.
Variable Listing:  See METHODOLOGICAL INFORMATION below.
       
   
2. Are there multiple versions of the dataset?
NO
   


--------------------------
METHODOLOGICAL INFORMATION
--------------------------


1. Description of methods used for collection/generation of data: 
 
VARIABLE: DESCRIPTION  


“transect”: The transect or grid along which the frost table depth was collected.
“transpoint”: The exact point along each transect or grid at which a frost table depth was collected. 
“ftd_hum”: Frost table depth measured in the hummock at the transpoint.
“ftd_interh”: Frost table depth measured in the inter-hummock at the transpoint.
“ftd_avg”: Average of hummock and inter-hummock frost table depth at each transpoint.
“humht”: The height of the hummock at each transpoint.
“bowldepth”: Calculated by subtracting the inter-hummock frost table depth and hummock height from the hummock frost table depth. Positive numbers indicate that the hummock frost table is sitting below the inter-hummock frost table (i.e., a frost table “bowl” has formed under the hummock)
“slope”: The angle (°) of the hillslope, with 0° representing a perfectly flat landscape. 
“snowdepth”: The snow depth at each transpoint before snowmelt began. 
“aspect”: The aspect of the hillslope (°), where 0° represents North, 90° is East, 180° is South, and 270° is West. 
“landcover”: The dominant vegetation type at the transpoint. This was either:
   shrub free tundra, “tundra”  
   birch shrubs “birch”  
   alder shrubs “alder”  
   tall mixed shrubs in a stream channel “channel”   
“snfr_day”: The day of year at which the transpoint became snow free. 
“date.j”: The day of year that the frost table depth measurements were made. 


2. Methods for processing the data:


VARIABLE: DESCRIPTION  


“slope”: Calculated using a bare ground digital elevation model in ArcGIS 10.5.
“snowdepth”: This was measured by differencing a digital surface model of the snow, as derived from photos from an unmanned aerial system, from a bare-ground digital surface model. The snow digital surface model was calculated using Pix4D. 
“aspect”: Calculated using a bare ground digital elevation model in ArcGIS 10.5.
“landcover”: Determined by visual inspection of snow-free drone imagery in ArcGIS 10.5
“snfr_day”: Determined using multiple unmanned aerial system image acquisitions taken over the course of the snow-melt period. Data was processed in ArcGIS 10.5




3. Instrument- or software-specific information needed to interpret the data:


None, data is already processed and ready to be used. 


4. Describe any quality-assurance procedures performed on the data:


Physically-impossible outliers were checked for in the dataset, but none existed.