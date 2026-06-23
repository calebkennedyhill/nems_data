import re
import json
import requests
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'

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

target_municipalities = [
    # Connecticut
    "Groton town, New London County, Connecticut",
    "New Haven town, New Haven County, Connecticut",
    "Norwalk town, Fairfield County, Connecticut",
    
    # Maine
    "Bath city, Sagadahoc County, Maine",
    "Portland city, Cumberland County, Maine",
    "South Portland city, Cumberland County, Maine",
    
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
    
    # New Hampshire
    "Concord city, Merrimack County, New Hampshire",
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
    "Brattleboro town, Windham County, Vermont",
    "Burlington city, Chittenden County, Vermont",
    "Hartford town, Windsor County, Vermont",
    "South Burlington city, Chittenden County, Vermont",
    "Williston town, Chittenden County, Vermont"
]

target_years = [
    2010,
    2014,
    2018,
    2023,
    2024
]
# variables: https://api.census.gov/data/2024/acs/acs5/variables.html?key=[CENSUS_API_KEY]
variables = {
    "B01003_001E": "total_population",

    "B25003_001E": "total_occupied_housing_units",
    "B25003_003E": "renter_occupied_housing_units",

    # income
    "B25070_002E": "perc_rent_of_income_0-10",
    "B25070_003E": "perc_rent_of_income_10-14.9",
    "B25070_004E": "perc_rent_of_income_15-19.9",
    "B25070_005E": "perc_rent_of_income_20-24.9",
    "B25070_006E": "perc_rent_of_income_25-29.9",
    "B25070_007E": "perc_rent_of_income_30-34.9",
    "B25070_008E": "perc_rent_of_income_35-39.9",
    "B25070_009E": "perc_rent_of_income_40-44.9",
    "B25070_010E": "perc_rent_of_income_50-100",
    "B25070_011E": "perc_rent_of_income_not_computed",

    # rental housing type
    "B25032_014E": "detached_units_1",
    "B25032_015E": "attached_units_1",
    "B25032_016E": "attached_units_2",
    "B25032_017E": "attached_units_3-4",

    "B25032_018E": "attached_units_5-9",
    "B25032_019E": "attached_units_10-19",
    "B25032_020E": "attached_units_20-49",
    "B25032_021E": "attached_units_50+",

    # heating fuel
    # NOTE: not renter specific
    "B25040_002E": "heating_utility_gas",
    "B25040_003E": "heating_bottled_gas",
    "B25040_004E": "heating_electricity",
    "B25040_005E": "heating_oil",
    "B25040_006E": "heating_coal_coke",
    "B25040_007E": "heating_wood",
    "B25040_008E": "heating_solar",
    "B25040_009E": "heating_other",
    "B25040_010E": "heating_none",

    # rental housing age
    "B25037_003E": "median_structure_built_year"
    }


# name parsing to make things easier to read
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

# metadata: https://api.census.gov/data/2024/acs/acs5/groups/B25036.json?key=[CENSUS_API_KEY]
# helper functions for age-related variables
def get_b25036_metadata(year):
    """
    Download universal ACS metadata and filter for B25036 variables.

    This endpoint is stable across ACS vintages.
    """

    url = f"https://api.census.gov/data/{year}/acs/acs5/groups/B25036.json"+"?key="+CENSUS_API_KEY

    response = requests.get(url)
    response.raise_for_status()

    all_variables = response.json().get("variables", {})

    b25036_metadata = {
        variable: info
        for variable, info in all_variables.items()
        if (
            variable.startswith("B25036_") and variable.endswith("E") 
            )
    }

    return b25036_metadata


def parse_construction_range(label):

    if not isinstance(label, str):
        return None

    normalized = (
        label.lower()
        .replace("-", " ")
        .replace("—", " ")
        .replace("–", " ")
    )

    built_match = re.search(r"built (.*)", normalized)

    if built_match is None:
        return None

    built_text = built_match.group(1)

    # Built aaaa to bbbb
    match = re.search(r"(\d{4}) to (\d{4})", built_text)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Built xxxx or later
    match = re.search(r"(\d{4}) or later", built_text)
    if match:
        return int(match.group(1)), None

    # Built yyyy or earlier
    match = re.search(r"(\d{4}) or earlier", built_text)
    if match:
        return None, int(match.group(1))

    return None


def get_relevant_variables(year):
    """
    Construct a metadata dictionary for renter-occupied construction periods.
    """

    # universe, 
    metadata = get_b25036_metadata(year)

    parsed_variables = {}

    for variable, info in metadata.items():

        label = info.get("label", "")
        # print("\n", label, "\n")

        # Restrict to renter-occupied housing units
        if "Renter occupied" not in label:
            continue

        parsed_range = parse_construction_range(label)
        # print("\n", parsed_range, "\n")

        if parsed_range is None:
            continue

        start_year, end_year = parsed_range

        def rename_var(start_year, end_year):
            if start_year is None:
                return "built_pre_" + str(end_year)
            
            if end_year is None:
                return "built_" + str(start_year) + "_to_" + str(year)
            
            return "built_" + str(start_year) + "_to_" + str(end_year)
        
        parsed_variables[variable] = rename_var(start_year, end_year)
        # {
        #     "start_year": start_year,
        #     "end_year": end_year,
        #     "label": label,
        #     "to_be_called": rename_var(start_year, end_year)
        # }

    return parsed_variables #universe, parsed_variables


def find_housing_age_data(target_states, target_municipalities, target_years
        # target_years
        ):
    c = Census(CENSUS_API_KEY)

    all_raw_data = []
    # df = pd.DataFrame()

    print("\n\n\n\n\t\t...querying...\t\tHOUSING AGE")
    
    for year in target_years:

        try:

            print(f"\n -- processing metadata for {year}...")
            
            # new_universe, 
            age_variables = get_relevant_variables(year)
            # all_universes.add(new_universe)
            
            fields = ["NAME"] + list(age_variables.keys())
            print(
                "\tdone. metadata is " +
                ("not empty." if bool(age_variables) else "empty.")
                )

            # Loop through each state
            for state_name, state_fips in target_states.items():

                print(f" -- grabbing {state_name}...")
                
                raw_data = c.acs5.state_county_subdivision(
                    fields,
                    state_fips,
                    Census.ALL,
                    Census.ALL,
                    year=year
                )
                print(
                    f"\tquery success: {state_name} in {year}." 
                    if bool(raw_data) 
                    else f"query failed: {state_name} in {year}."
                )
                
                for row in raw_data:
                    row["year"] = year

                all_raw_data.extend(raw_data)

        except Exception as e:

            print(f"    [!] Error completely skipping year {year}: {e}")

    df = pd.DataFrame(all_raw_data)

    df_filtered = df[ df['NAME'].isin(target_municipalities) ].copy()
    df_filtered.rename(columns=age_variables, inplace=True)
    df_filtered.sort_values(by=["NAME", "year"], inplace=True)

    final_columns = ["year", "NAME"] + list(age_variables.values())
    output = df_filtered[final_columns]

    # split name
    output[
        ["name", "muni_type", "county", "state"]
    ] = output["NAME"].apply(parse_acs5_cousub_name)
    output.drop(columns=["NAME"], inplace=True)
    output.sort_values(by=["state", "name", "year"], inplace=True)

    # reorder cols
    first_cols = ["year", "name", "muni_type", "county", "state"]
    last_cols = [col for col in output.columns if col not in first_cols]
    output = output[first_cols + last_cols]

    return output
    


def get_non_age_data(target_states, target_municipalities, target_years, variables):

    c = Census(CENSUS_API_KEY)
    fields = ["NAME"] + list(variables.keys())

    all_raw_data = []

    print("\n\n\n\n\t\t...querying...\t\tNON-AGE-RELATED")

    for year in target_years:

        for state_name, state_fips in target_states.items():
            print(f" -- grabbing {state_name} for {year}...")
            
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


    df = pd.DataFrame(all_raw_data)

    df_filtered = df[ df['NAME'].isin(target_municipalities) ].copy()
    df_filtered.rename(columns=variables, inplace=True)
    df_filtered.sort_values(by=["NAME", "year"], inplace=True)

    final_columns = ["year", "NAME"] + list(variables.values())
    output = df_filtered[final_columns]


    # compute NEMS metrics
    output["renter_share"] = round(100.00*output["renter_occupied_housing_units"]/output["total_occupied_housing_units"], 2)
    output["renter_share_change"] = output.groupby("NAME")["renter_share"].diff()


    output["attached_units_2-4"] = output["attached_units_2"] + output["attached_units_3-4"]

    output["attached_units_5+"] = (
        output["attached_units_5-9"] + \
        output["attached_units_10-19"] + \
        output["attached_units_20-49"] + \
        output["attached_units_50+"]
        )
    output = output.drop(columns=[
        "attached_units_5-9", 
        "attached_units_10-19", 
        "attached_units_20-49", 
        "attached_units_50+"
        ])


    # split name
    output[
        ["name", "muni_type", "county", "state"]
    ] = output["NAME"].apply(parse_acs5_cousub_name)
    output.drop(columns=["NAME"], inplace=True)
    output.sort_values(by=["state", "name", "year"], inplace=True)

    # reorder cols
    first_cols = ["year", "name", "muni_type", "county", "state"]
    last_cols = [col for col in output.columns if col not in first_cols]
    output = output[first_cols + last_cols]

    return output


# combine age- and non-age-related data into one df
def get_all_data(target_states, target_municipalities, target_years, variables):
    df_age = find_housing_age_data(target_states, target_municipalities, target_years)
    df_non_age = get_non_age_data(target_states, target_municipalities, target_years, variables)
    output = df_age.merge(
        df_non_age, 
        how='inner',
        on=["year", "name", "muni_type", "county", "state"]
        )
    return output.sort_values(by=["name", "muni_type", "county", "state", "year"])


get_all_data(
    target_municipalities = target_municipalities,
    target_states = target_states,
    target_years = target_years,
    variables = variables
).to_csv("./reports/asst_2_metrics_US.csv", sep=",", index=False)
