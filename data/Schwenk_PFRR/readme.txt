This readme was created by Jon Schwenk (jschwenk@lanl.gov) on January 13, 2025.

This collection of data represents multiple field trips to the Poker Flats Research Range (PFRR) outside of Fairbanks, AK. While all the data presented here were procured by LANL, the field work was done in collaboration with the National Geospatial Intelligence Agency (NGA), the University of Alaska, Fairbanks (UAF), and the Poker Flats Research Range itself. 

The overall mission of the field work was to collect information about the permafrost conditions at PFRR, including locating near surface permafrost and mapping its spatial distribution, quantifying the ice content of identified permafrost through soil coring, and measuring potential indicators of permafrost condition such as seasonal subsidence and thermal conditions. 

Data from four field trips and some lab work is provided in this package:
March 24 - March 30, 2024: Collect soil cores
May 12 - May 20, 2024: Pre-thaw-season drone flights (elevation, thermal, photogrammetry), installation of corner reflectors
September 6 - September 13, 2024: Post-thaw-season drone flights (repeat surveys/collection), adjustment of corner reflectors
September 22 - September 27. 2024: Frost probing (only one day at PFRR), adjustment of corner reflectors

There are three "types" of data in this package:
 - Coring: contains analysis of cores from PFRR. Most of this data was collected in LANL's laboratories after transporting the frozen cores from PFRR to LANL.
 - Drone: contains all data collected via drone, including LiDAR (elevations), thermal imaging (experimental), and photogrammetry (experimental). Also contains scripts used to process point clouds and create differenced DTMs, as well as our first-cut processing results.
 - Frost Probing: contains active layer depths for a number of locations around PFRR

Each data directory has its own readme presented as a Powerpoint file. These readmes describe the motivations of the work, the equipment used, the procedures followed, the people involved, and, when relevant, photos and/or maps to contexutalize the data.

Note that this data is fairly "raw" in the sense that the funding for this project ended when the thaw season was ending, so there was little-to-no funding to process the data beyond a minimal degree. This is especially relevant for the drone data for which changes were measured by differencing pre- and post- thaw season DTMs. However, raw data (e.g. point clouds) are provided along with the processing scripts so that users may re-process the data as they see fit.

Questions can be sent to Jon Schwenk (jschwenk@lanl.gov) who will direct them to the relevent individual(s).