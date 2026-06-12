import re
import json
import requests
import pandas as pd
import geopandas as gpd
pd.options.mode.chained_assignment = None  # default='warn'

from us import states
from census import Census

from setup import CENSUS_API_KEY

target_states = {
    "Maine": str(states.ME.fips)
}

target_municipalities = [
    "Bath city, Sagadahoc County, Maine",
    "Portland city, Cumberland County, Maine",
    "South Portland city, Cumberland County, Maine"
]

target_years = [2024]

variables = {
    "B01003_001E": "total_population",

    "B25003_001E": "total_occupied_housing_units",
    "B25003_003E": "renter_occupied_housing_units"
}

c = Census(CENSUS_API_KEY)
fields = ["NAME"] + list(variables.keys())

all_raw_data = []

print("\n\n\n\n\t\t...querying...")

for year in target_years:

    for state_name, state_fips in target_states.items():
        print(f" -- grabbing {state_name} for {year}...")
        
        try:
            # Query the API
            raw_data = c.acs5.state_county_subdivision(
                fields=fields, 
                state_fips=state_fips, 
                county_fips=Census.ALL, 
                subdiv_fips=Census.ALL, 
                year=year
            )
            
            for row in raw_data:
                row["year"] = year
            
            all_raw_data.extend(raw_data)
            
        except Exception as e:
            print(f"    [!] Error fetching {state_name} in {year}: {e}")


df = pd.DataFrame(all_raw_data)

output = df[ df['NAME'].isin(target_municipalities) ].copy()
output.rename(columns=variables, inplace=True)
output.sort_values(by=["NAME", "year"], inplace=True)
output.rename(columns={"county subdivision": "county_subdiv"}, inplace=True)

output["renter_share"] = round(100.00*output["renter_occupied_housing_units"]/output["total_occupied_housing_units"], 2)
output["renter_share_change"] = output.groupby("NAME")["renter_share"].diff()

output['GEOID'] = (
    output['state'].astype(str).str.zfill(2) + 
    output['county'].astype(str).str.zfill(3) + 
    output['county_subdiv'].astype(str).str.zfill(5)
)

tiger_url = "https://www2.census.gov/geo/tiger/TIGER2023/COUSUB/tl_2024_"+\
    str(states.ME.fips) + \
        "_cousub.zip"
gdf_shapes = gpd.read_file(tiger_url)

gdf = gdf_shapes.merge(output, on='GEOID', how='inner')

print(gdf.describe())