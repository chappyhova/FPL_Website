import pandas as pd
import requests
import json
import pickle
from natsort import natsorted
import numpy as np


def retrieve_data():
    # Pulling the data from the FPL website
    fpl_data = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
    with open('Data/2019-20/fpl.json', 'w') as f:
        json.dump(fpl_data, f)


def json_to_df(data):
    # Converting the main FPL data into a pickle file after being cleaned and shaped
    pd.set_option('display.max_colwidth', -1)
    file = open(data, 'r')
    fpl_data = json.load(file)
    fpl_data = pd.DataFrame(fpl_data['elements'])
    fpl_data = fpl_data.rename(columns={'element_type': 'new position', 'now_cost': 'new price',
                                        'selected_by_percent': 'new ownership', 'first_name': 'first name',
                                        'second_name': 'second name'})
    fpl_data['Player Name'] = fpl_data['first name'] + ' ' + fpl_data['second name']
    fpl_data = fpl_data[['Player Name', 'new position', 'new ownership', 'new price']]
    fpl_data['new position'] = (fpl_data['new position']).astype(str)
    fpl_data = positions(fpl_data)
    fpl_data.to_pickle("Data/2019-20/fpl.pickle")


def positions(data):
    # Changing element types to positions
    vals_to_replace = {'1': 'Goalkeeper', '2': 'Defender', '3': 'Midfielder', '4': 'Striker'}
    data['new position'] = data['new position'].map(vals_to_replace)
    return data


def combining_dfs():
    old_data = pd.read_pickle('Data/2018-19/fpl.pickle')
    for col in old_data.columns:
        print(col)
    new_data = pd.read_pickle('Data/2019-20/fpl.pickle')
    merged = pd.merge(old_data, new_data, on='Player Name', how='inner')
    merged = vapm(merged)
    merged = manipulating_data(merged)
    merged = merged[['Player Name', 'minutes', 'total points', 'non-appearance points', 'VAPM', 'value', 'NA-PP90',
                     'new price', 'position', 'new position', 'new ownership', 'team',
                     'big chances created', 'big chances missed', 'threat/90', 'creativity/90']]
    merged.columns = [x.title() for x in merged.columns]
    merged = rename(merged)
    merged = clean_df(merged)
    merged.to_pickle('Data/2019-20/merged.pickle')


def clean_df(data):
    # Cleaning the main FPL data and making it more readable
    data = data.round(2)
    data = data.fillna(0)
    return data


def rename(data):
    # Capitalising columns that use acronyms
    data = data.rename(columns={'Na-Pp90': 'NA-PP90', 'Vapm': 'VAPM'})
    return data


def vapm(data):
    # Calculating Value Added Per Million column
    data['VAPM'] = (data['non-appearance points'] / data['minutes']) / (data['new price']) * 10000
    return data


def manipulating_data(data):
    data['value'] = (data['total points'] / data['minutes']) / data['price'] * 10000
    data['non-appearance value'] = (data['non-appearance points'] / data['minutes']) / data['price'] * 10000
    data['NA-PP90'] = (data['non-appearance points'] / data['minutes']) * 90
    data['threat/90'] = (data['threat'] / data['minutes']) * 90
    data['creativity/90'] = (data['creativity'] / data['minutes']) * 90
    return data


retrieve_data()
json_to_df('Data/2019-20/fpl.json')
combining_dfs()
