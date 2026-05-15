Geomorphic mapping and permafrost occurrence on the Koyukuk River floodplain near Huslia, Alaska
Contact: Madison Douglas (mmdouglas@berkeley.edu)


Douglas M ; Blankenship R ; Chadwick A ; Dunne K ; Fischer W ; Geyman E ; Ke Y ; Kemeny P ; Li G ; Magyar J ; Mutter E ; Nghiem J ; Piliouras A ; Reahl J ; Rowland J ; Schwenk J ; Seelen E ; Smith M I ; West A J ; Lamb M (2023): Geomorphic mapping and permafrost occurrence on the Koyukuk River floodplain near Huslia, Alaska. Incorporating the Hydrological Controls on Carbon Cycling in Floodplain Ecosystems into Earth System Models (ESMs), ESS-DIVE repository. Dataset. doi:10.15485/2204419 accessed via https://data.ess-dive.lbl.gov/datasets/doi:10.15485/2204419 on 2025-01-31


Overview and methods
       All datasets are projected in WGS84. Geomorphic mapping was done by hand in QGIS 3.4 on Landsat ~30-m and Worldview 2-m imagery. Mapping includes geomorphic landforms visible on the floodplain, the relative age of groups of landforms based on cross-cutting relationships, and inferred prior paths of the river based on the location of oxbow lakes.
       Permafrost occurrence was measured through probing, coring or digging sampling pits, and direct observation of ground ice in riverbanks. The depth of thaw was measured in the vertical direction on the floodplain surface and in the horizontal direction on steep, exposed faces of eroding riverbanks. 



PermafrostMeasurements.csv
       Field measurements and observations of permafrost presence/absence in June 27 to July 8, 2018 and September 26 to October 1, 2022.
       ID: measurement identifier
       Method: method by which permafrost was inferred to be present or absent at each location, either permafrost probing (1m or 2m probe length), digging and taking sediment cores for sampling (dig/core), or observations of frozen riverbanks with ground ice exposed at the surface (observation)
       Permafrost: reads either "Y" or "N" for whether permafrost was detected at that location
       Year: either 2018 or 2022 to indicate when the measurement was taken
       Horizontal_distance_m: distance in meters along a transect of the ground surface
       Depth_to_permafrost_cm: depth to permafrost in centimeters at this location
       Depth_cm: depth in centimeters along a vertical transect of an eroding riverbank
       Horizontal_to_permafrost_cm: depth to permafrost measured horizontally in centimeters into an eroding riverbank
       Latitude: in decimal degrees, WGS84
       Longitude: in decimal degrees, WGS84
       Relative_age: numerical relative age assigned using RelativeAge_shapefile
       Geomorphic_unit: numerical geomorphic unit assigned using GeomorphLandforms_shapefile
       
       
CUSP Processing Notes:
Only 2022 data from this dataset is used. 2018 data already inmported from the Koyukuk_2018 data.
At locations with multiple measurements either vertically on river bank faces or on transects only presence absence of permafrost is retained
       