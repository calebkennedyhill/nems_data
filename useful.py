import re
import sys
import json
import requests
import numpy as np
import pandas as pd
import geopandas as gpd

from us import states
from census import Census

from setup import CENSUS_API_KEY

target_states = {
    "Connecticut": str(states.CT.fips),
    "Maine": str(states.ME.fips),
    "Massachusetts": str(states.MA.fips),
    "New Hampshire": str(states.NH.fips),
    "Rhode Island": str(states.RI.fips),
    "Vermont": str(states.VT.fips)
}

nems_munis = [
    # Connecticut
    "Groton town, New London County, Connecticut",
    "New Haven town, New Haven County, Connecticut",
    "Norwalk town, Fairfield County, Connecticut",

    # Massachusetts
    "Amherst town, Hampshire County, Massachusetts",
    "Arlington town, Middlesex County, Massachusetts",
    "Beverly city, Essex County, Massachusetts",
    "Boston city, Suffolk County, Massachusetts",
    "Cambridge city, Middlesex County, Massachusetts",
    "Concord town, Middlesex County, Massachusetts",
    "Dedham town, Norfolk County, Massachusetts",
    "Greenfield city, Franklin County, Massachusetts",
    "Lexington town, Middlesex County, Massachusetts",
    "Medford city, Middlesex County, Massachusetts",
    "New Bedford city, Bristol County, Massachusetts",
    "Northampton city, Hampshire County, Massachusetts",
    "Provincetown town, Barnstable County, Massachusetts",
    "Somerville city, Middlesex County, Massachusetts",
    "Winchester town, Middlesex County, Massachusetts",

    # Maine
    "Acton town, York County, Maine",
    "Alfred town, York County, Maine",
    "Arundel town, York County, Maine",
    "Baldwin town, Cumberland County, Maine",
    "Bath city, Sagadahoc County, Maine",
    "Berwick town, York County, Maine",
    "Biddeford city, York County, Maine",
    "Brownfield town, Oxford County, Maine",
    "Buxton town, York County, Maine",
    "Cornish town, York County, Maine",
    "Dayton town, York County, Maine",
    "Denmark town, Oxford County, Maine",
    "Eliot town, York County, Maine",
    "Fryeburg town, Oxford County, Maine",
    "Hiram town, Oxford County, Maine",
    "Hollis town, York County, Maine",
    "Kennebunk town, York County, Maine",
    "Kennebunkport town, York County, Maine",
    "Kittery town, York County, Maine",
    "Lebanon town, York County, Maine",
    "Limerick town, York County, Maine",
    "Limington town, York County, Maine",
    "Lovell town, Oxford County, Maine",
    "Lyman town, York County, Maine",
    "Newfield town, York County, Maine",
    "North Berwick town, York County, Maine",
    "Ogunquit town, York County, Maine",
    "Old Orchard Beach town, York County, Maine",
    "Parsonsfield town, York County, Maine",
    "Porter town, Oxford County, Maine",
    "Portland city, Cumberland County, Maine",
    "Saco city, York County, Maine",
    "Sanford city, York County, Maine",
    "Shapleigh town, York County, Maine",
    "South Berwick town, York County, Maine",
    "South Portland city, Cumberland County, Maine",
    "Stoneham town, Oxford County, Maine",
    "Stow town, Oxford County, Maine",
    "Sweden town, Oxford County, Maine",
    "Waterboro town, York County, Maine",
    "Wells town, York County, Maine",
    "York town, York County, Maine",

    # New Hampshire
    "Dover city, Strafford County, New Hampshire",
    "Exeter town, Rockingham County, New Hampshire",
    "Hanover town, Grafton County, New Hampshire",
    "Keene city, Cheshire County, New Hampshire",
    "Lebanon city, Grafton County, New Hampshire",
    "Nashua city, Hillsborough County, New Hampshire",
    "Portsmouth city, Rockingham County, New Hampshire",

    # Rhode Island
    "Cranston city, Providence County, Rhode Island",
    "Pawtucket city, Providence County, Rhode Island",
    "Providence city, Providence County, Rhode Island",

    # Vermont
    "Bolton town, Chittenden County, Vermont",
    "Brattleboro town, Windham County, Vermont",
    "Buels gore, Chittenden County, Vermont",
    "Burlington city, Chittenden County, Vermont",
    "Charlotte town, Chittenden County, Vermont",
    "Colchester town, Chittenden County, Vermont",
    "Essex town, Chittenden County, Vermont",
    "Essex Junction city, Chittenden County, Vermont", 
    "Hartford town, Windsor County, Vermont",
    "Hinesburg town, Chittenden County, Vermont",
    "Huntington town, Chittenden County, Vermont",
    "Jericho town, Chittenden County, Vermont",
    "Milton town, Chittenden County, Vermont",
    "Richmond town, Chittenden County, Vermont",
    "Shelburne town, Chittenden County, Vermont",
    "South Burlington city, Chittenden County, Vermont",
    "St. George town, Chittenden County, Vermont",
    "Underhill town, Chittenden County, Vermont",
    "Westford town, Chittenden County, Vermont",
    "Williston town, Chittenden County, Vermont",
    "Winooski city, Chittenden County, Vermont"
]

def check_nems_membership(name: str):
    if name in nems_munis:
        return True
    return False


def parse_acs5_cousub_name(name_string):

        # Split on commas first
        parts = name_string.split(",")

        # Left side:
        # "Exeter town"
        left = parts[0].strip()

        # County:
        # "Rockingham County"
        county = parts[1].replace("County", "").strip()

        # State:
        # "New Hampshire"
        state = parts[2].strip()

        # Split municipality name/type
        left_parts = left.split()

        muni_type = left_parts[-1]

        name = " ".join(left_parts[:-1])

        return pd.Series([
            name,
            muni_type,
            county,
            state
        ])

def acs_df_from_raw(all_raw_data, rename_dict:dict):
    output = pd.DataFrame(all_raw_data)
    output["GEOID"] = output["state"] + output["county"] + output["county subdivision"]

    output["nems"] = output["NAME"].apply(check_nems_membership)
    output.rename(columns=rename_dict, inplace=True)


    output[
            ["name_str", "muni_str", "county_str", "state_str"]
        ] = output["NAME"].apply(parse_acs5_cousub_name)
    output.drop(columns=["NAME"], inplace=True)
    output.sort_values(by=["GEOID", "year"], inplace=True)

    return output

def vars_and_moes(var_dict: dict) -> dict:
    new_dict: dict = {}

    for key in var_dict:
        new_dict[key+"E"] = var_dict[key]
    for key in var_dict:
        new_dict[key+"M"] = var_dict[key]+"_m"
    return new_dict

def cousub_states_years_variables(
        target_states:dict, target_years:list, prefixes:dict, 
        loud=True) -> pd.DataFrame:
    
    # import sys
    # from datetime import datetime
    # old_stdout = sys.__stdout__
    # log_file = open("pipeline_nb.log", "a")
    # sys.stdout = log_file

    variables = vars_and_moes(prefixes)
    
    c = Census(CENSUS_API_KEY)
    fields = ["NAME"] + list(variables.keys())

    all_raw_data = []

    if loud:
        # print("\n\t\tquerying: " +datetime.now().strftime("%Y-%m-%d %H:%M:%S") +"\n")
        print("variables of interest:\n")
        for k in variables:
            print(k+": "+variables[k])
        print("\n")

    for year in target_years:

        for state_name, state_fips in target_states.items():
            if loud:
                print(f" -- grabbing {state_name} for {year}.")
            
            try:
                # Query the API
                raw_data = c.acs5.state_county_subdivision(
                    fields, 
                    state_fips, 
                    Census.ALL, 
                    Census.ALL, 
                    year=year
                )
                
                for row in raw_data:
                    row["year"] = year
                
                all_raw_data.extend(raw_data)
                
            except Exception as e:
                print(f"    [!] Error fetching {state_name} in {year}: {e}")


    # output = acs_df_from_raw(all_raw_data, variables)
    output = pd.DataFrame(all_raw_data)
    output.rename(columns=variables, inplace=True)
    output['GEOID'] = output['state'] + output['county'] + output['county subdivision']
    output[
            ["name_str", "muni_str", "county_str", "state_str"]
        ] = output["NAME"].apply(parse_acs5_cousub_name)
    output.drop(columns=["NAME"], inplace=True)

    """ 
    WARNING: 
        Very hacky name changing here.
        Would love to find a better approach, but this is what I've got for now.
    """
    output.loc[output['name_str']=='Amherst Town', 'nems']=True
    output.loc[output['name_str']=='Amherst Town', 'name_str']='Amherst'

    # "Groton town, New London County, Connecticut",
    # "New Haven town, New Haven County, Connecticut",
    # "Norwalk town, Fairfield County, Connecticut"
    output.loc[(output['name_str']=='Groton') & (output['state_str']=="Connecticut"), 'nems'] = True
    output.loc[(output['name_str']=='New Haven') & (output['state_str']=="Connecticut"), 'nems'] = True
    output.loc[(output['name_str']=='Norwalk') & (output['state_str']=="Connecticut"), 'nems'] = True

    # keys = list(prefixes.values())
    # for k in keys:
    #     output[k+"_cv"] = np.where(
    #         output[k]!=0,
    #         round( (output[k+"_m"]/1.645)/output[k], 2 ),
    #         0
    #         )

    # sys.stdout = old_stdout
    # log_file.close()
    
    return output



def tract_states_years_variables(
        target_states:dict, target_years:list, prefixes:dict, 
        loud=False) -> pd.DataFrame:

    variables = vars_and_moes(prefixes)
    
    c = Census(CENSUS_API_KEY)
    fields = ["NAME"] + list(variables.keys())

    all_raw_data = []

    from datetime import datetime
    if loud:
        print("\n\t\tquerying: " +datetime.now().strftime("%Y-%m-%d %H:%M:%S") +"\n")
        print("variables of interest:\n")
        for k in variables:
            print(k+": "+variables[k])
        print("\n")

    for year in target_years:

        for state_name, state_fips in target_states.items():
            if loud:
                print(f" -- grabbing {state_name} for {year}.")
            
            try:
                # Query the API
                raw_data = c.acs5.state_county_tract(
                    fields, 
                    state_fips, 
                    Census.ALL, 
                    Census.ALL, 
                    year=year
                )
                
                for row in raw_data:
                    row["year"] = year
                
                all_raw_data.extend(raw_data)
                
            except Exception as e:
                print(f"    [!] Error fetching {state_name} in {year}: {e}")


    output = pd.DataFrame(all_raw_data)
    output.rename(columns=variables, inplace=True)
    output['GEOID'] = output['state'] + output['county'] + output['tract']

    keys = list(prefixes.values())
    for k in keys:
        output[k+"_cv"] = np.where(
            output[k]!=0,
            round( (output[k+"_m"]/1.645)/output[k], 2 ),
            0
            )

    
    return output



def aggregate(df:pd.DataFrame, agg_name:str, to_agg:list, drop=False) -> pd.DataFrame:

    output = df.copy()
    to_agg_m = [v+"_m" for v in to_agg]
    output[agg_name] = output[to_agg].sum(axis=1)
    output[agg_name+"_m"] = np.sqrt( (output[to_agg_m]**2).sum(axis=1) )
    output[agg_name+"_cv"] = np.where(output[agg_name]>0,
        (output[agg_name+"_m"]/1.645)/output[agg_name],
        0
    )
    if drop:
        to_drop = to_agg + [v+"_m" for v in to_agg] + [v+"_cv" for v in to_agg]
        output.drop(columns=to_drop,inplace=True)

    return output

# See p. 61-64 of 2020 ACS handbook
# https://www.census.gov/content/dam/Census/library/publications/2020/acs/acs_general_handbook_2020.pdf
def proportion(df:pd.DataFrame, new_name:str, num:str, denom:str) -> pd.DataFrame:
    output = df.copy()

    X = output[num]
    Y = output[denom]
    X_m = output[f"{num}_m"]
    Y_m = output[f"{denom}_m"]

    P = np.where(Y > 0, X / Y, 0)
    output[new_name] = np.round(P * 100.00, 2)
    
    moe_p = np.where(
        Y > 0,
        (1 / Y) * np.sqrt(np.clip(X_m**2 - (P**2 * Y_m**2), 0, None)),
        0
    )
    
    output[f"{new_name}_m"] = moe_p * 100
    with np.errstate(divide='ignore', invalid='ignore'):
        output[f"{new_name}_cv"] = np.where(P != 0, (moe_p / 1.645) / P, 0)
    
    return output


def cv_analysis(incentive_df:pd.DataFrame, category="", threshold=0.3):
    print("\nPercentage of "+category+"variables above threshold: ",threshold)
    
    print("High CV variables, NEMS: (percent)")
    for var in incentive_df.columns:
        if str(var).endswith("_cv"):
            print(f"{var} - - - - ",
                round( 100.00*len(incentive_df.loc[(incentive_df[var]>threshold) & (incentive_df["nems"]==True)])/len(incentive_df), 2)
            )
    print("")
    print("High CV variables, ALL: (percent)")
    for var in incentive_df.columns:
        if str(var).endswith("_cv"):
            print(f"{var} - - - -  ",
                round( 100.00*len(incentive_df.loc[(incentive_df[var]>threshold) ])/len(incentive_df), 2)
            )



def main() -> None:
    print('useful.py: main() called.')

if __name__ == '__main__':
    main()