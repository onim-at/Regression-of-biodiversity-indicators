#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 28 13:39:15 2020

@author: vincenzomadaghiele
"""


import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Polygon


base_url = "https://api.gbif.org/v1/occurrence/search?"

def get_GBIF_response(base_url, offset, params, df):
    """Performs an API call to the base URL with additional parameters listed in 'params'. 
    Concatenates response to a Pandas DataFrame, 'df'."""
    
    #Construct the query URL
    query = base_url+'&'+f'offset={offset}'
    for each in params:
        query = query+'&'+each
    
    #Call API
    response = requests.get(query)
    
    #If call is successful, add data to df
    if response.status_code != 200:
        print(f"API call failed at offset {offset} with a status code of {response.status_code}.")
    else:
        result = response.json()
        df_concat = pd.concat([df, pd.DataFrame.from_dict(result['results'])], axis = 0, ignore_index = True, sort = True)
        endOfRecords = result['endOfRecords']
        return df_concat, endOfRecords, response.status_code


#%% Get the data from GBIF API

x1 = 17.17163
y1 = 40.26192
x2 = 18.07251
y2 = 40.26192
x3 = 18.07251
y3 = 40.76307
x4 = 17.17163
y4 = 40.76307
x5 = 17.17163
y5 = 40.26192

# insert the polygon coordinates here
# puglia polygon
#polygon ='POLYGON((17.17163 40.26192,18.07251 40.26192,18.07251 40.76307,17.17163 40.76307,17.17163 40.26192))'

# france polygon
#polygon = 'POLYGON((3.5 44,5 44,5 45,3.5 45,3.5 44))'

#set parameters for API call
#params = ['limit=300', 'hasCoordinate=true', 'hasGeospatialIssue=false', 'geometry='+polygon, ]
 
lat_range = '44,45'
lon_range = '3.5,5'
kingdom_key = '6' # kingdom: plantae
params = ['limit=300', 'hasCoordinate=true', 'hasGeospatialIssue=false', 'decimalLatitude='+lat_range, 'decimalLongitude='+lon_range, 'kingdomKey='+kingdom_key ]
#Set up a simple while loop to continue downloading until the last #page
df = pd.DataFrame()
endOfRecords = False
offset = 0
status = 200

while endOfRecords == False and status == 200:
    df, endOfRecords, status = get_GBIF_response(base_url, offset, params, df)
    offset = len(df) + 1
    
    
#%% cut the columns 'decimalLatitude' and 'decimalLongitude' to 0.01 precision
# count unique species (.groupBy(['lat','lon'])['species'].nunique())
# create dataset with only 'lat', 'lon', 'num_species'
# export to csv the first one and the second one
    
def cutLat(row):
    return int(row['latitude']*100)/100
def cutLon(row):
    return int(row['longitude']*100)/100

export_path = 'data/GBIF_france.csv'
land_data.to_csv(export_path, index = True)

df['decimalLatitude'] = df.apply(cutLat, axis=1)
df['decimalLongitude'] = df.apply(cutLon, axis=1)

export_path = 'data/GBIF_france_cutLatLon.csv'
land_data.to_csv(export_path, index = True)

unique_species_count = df.groupBy(['decimalLatitude','decimalLongitude'])['species'].nunique().reset_index()

export_path = 'data/GBIF_france_unique_species_count.csv'
land_data.to_csv(export_path, index = True)


    
#%% Plot by grid cell

# Import species data into a GeoDataFrame
species_gdf = gpd.GeoDataFrame(df, 
              geometry=gpd.points_from_xy(df['decimalLongitude'], 
                                          df['decimalLatitude']),  
              crs = "EPSG:4326")

# Create GeoDataFrame with 1/10th degree grid cells

#Make list of 1 degree grid cells with shapely polygons
long_range = list(i/10 for i in range(30,50)) 
lat_range = list(i/10 for i in range(430,450))

poly_list = []
for x in long_range:
    for y in lat_range:
        new_poly = Polygon([(x, y), 
                            (x + 0.09999, y), 
                            (x + 0.09999, y + 0.09999), 
                            (x, y + 0.09999)])
        poly_list.append(new_poly)

#%% Initialize the cells

#Make GeoDataFrame from list of polygons, making sure that the 
#coordinate reference system aligns with your data points DF
grid_df_1d = gpd.GeoDataFrame(geometry = poly_list, crs = species_gdf.crs)

#Add a column of cell numbers for visualization purposes
grid_df_1d['cell_no'] = list(range(0, len(grid_df_1d)))

#Calculate the number of species in each grid cell
#Make a dictionary to store a list of each grid cell's species
grid_species = {}
for x in list(range(0, len(grid_df_1d))):
    grid_species[f'{x}'] = []


#For each species in the species dataframe, determine whether or not 
#it's within the bounds of the polygons in the grid dataframe. If it 
#is, add that species to the list in the grid_species dict 
for ind_s, val_s in species_gdf.iterrows():
    for ind_g, val_g in grid_df_1d.iterrows(): 
        if val_s['geometry'].within(val_g['geometry']):
            grid_species[f"{val_g['cell_no']}"].append(val_s['species'])


#Count the number of unique species in each list and save in a 
# new dictionary and then add data to the grid dataframe
grid_counts = {}
for k, v in grid_species.items():
    #v.dropna(inplace = True)
    v = list(filter(None, v)) 
    grid_counts[k] = len(np.unique(v))
    
grid_df_1d['species_count'] = np.zeros(len(grid_df_1d))
for k, v in grid_counts.items():
    grid_df_1d.loc[int(k) ,'species_count'] = v

#Drop cells that don't have any species in them
grid_df_1d_nozero = grid_df_1d.drop(grid_df_1d[grid_df_1d['species_count'] == 0].index, axis = 0)

#%% Plot the grid

countries = gpd.read_file("data/ne_50m_admin_0_countries/ne_50m_admin_0_countries.shp", encoding = 'UTF-8')
fig, ax = plt.subplots(1, 1, figsize = (10, 10))
countries.plot(ax = ax, color = 'whitesmoke')
grid_df_1d_nozero.plot(column = 'species_count', 
                       ax = ax, 
                       legend = True, 
                       cmap = 'YlOrRd',
                       legend_kwds={'label': "Number of Species", 
                                    'shrink': 0.5})
ax.set_facecolor('lightblue')
plt.xlabel('Longitude')
plt.ylabel('Latitude')
plt.title(r"Biodiversity of France-region by grid cell", fontdict = {'fontsize': 'x-large'})
plt.xlim((3, 5))
plt.ylim((43, 45))
plt.tight_layout()

#%% Export to csv (RUN THIS!!)
normal_df = pd.DataFrame(grid_df_1d_nozero)
export_path = 'data/france_GBIF.csv'
normal_df.to_csv(grid_df_1d_nozero, index = True)

