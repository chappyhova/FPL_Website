# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, request
import pandas as pd
import requests
import json
import pickle
from natsort import natsorted
import numpy as np

app = Flask(__name__)


@app.route('/')
def render():
    with open('C:/Users/Chappy/PycharmProjects/FPL_Website/Data/fpl.pickle', 'rb') as f:
        data = pickle.load(f)
    return render_template('index.html', data=data.to_html(escape=False, index=False, classes='my_class" id = "fpl'))


@app.route('/', methods=["GET", "POST"])
def teams():
    if request.method == "POST":
        with open('C:/Users/Chappy/PycharmProjects/FPL_Website/Data/fpl.pickle', 'rb') as f:
            data = pickle.load(f)
        new_data = form(data, request.form['last-x-games'])
        new_data = clean_df(new_data)
        return render_template('index.html', data=new_data.to_html(escape=False, index=False, classes='my_class" id = "fpl'))




@app.route('/player/<number>')
def player(number):
    data = load_df('Data/players_pickle/1.pickle')
    print(number)
    return render_template('player.html', data=data.to_html(escape=False))


if __name__ == '__main__':
    app.run()


def retrieve_data():
    # Pulling the data from the FPL website
    fpl_data = requests.get('https://fantasy.premierleague.com/drf/bootstrap-static').json()
    with open('Data/fpl.json', 'w') as f:
        json.dump(fpl_data, f)


def player_total(data):
    # Returns the number of players in the data
    num_of_players = (len(data))
    return num_of_players


def player_urls(total):
    # Creates a list containing the url for each player
    player_link = 'https://fantasy.premierleague.com/drf/element-summary/'
    url_list = []

    for i in range(1, total + 1):
        player_address = player_link + str(i)
        url_list.append(player_address)

    return url_list


def get_players():
    # Iterates through the player url list and saves a copy of each player's data as a json file
    counter = 1
    for player in player_urls(player_total(load_df('Data/fpl.pickle'))):
        data = requests.get(player).json()
        print(counter)
        with open('Data/players/' + str(counter) + '.json', 'w') as f:
            json.dump(data, f)
        counter += 1


def clean_players():
    # Shaping the player data and saving as a pickle
    counter = 1
    for file_name in natsorted(os.listdir('Data/players')):
        file = open('Data/players/' + file_name, 'r')
        data = json.load(file)

        data = pd.DataFrame(data['history'])
        data = data.rename(
            columns={'opponent_team': 'opponent', 'was_home': 'was home', 'total_points': 'total points',
                     'big_chances_created': 'big chances created', 'big_chances_missed': 'big chances missed'})
        # Creating a column for non-appearance points
        for index, row in data.iterrows():
            if row['minutes'] > 59:
                data.loc[index, 'non-appearance points'] = row['total points'] - 2
            elif row['minutes'] > 0:
                data.loc[index, 'non-appearance points'] = row['total points'] - 1
            else:
                data.loc[index, 'non-appearance points'] = 0
        # Creating a column for number of times the player has played 75 minutes or more
        for index, row in data.iterrows():
            if row['minutes'] > 74:
                data.loc[index, 'over 75 mins'] = True
            else:
                data.loc[index, 'over 75 mins'] = False
        # Saving the data required. Also preventing an error that is thrown when a new player to the Premier League has no data
        if not data.empty:
            data = data[['non-appearance points', 'over 75 mins', 'big chances created', 'big chances missed', 'minutes']]
            save_df(data, 'Data/players_pickle/' + str(counter) + '.pickle')
        else:
            data = pd.DataFrame(columns=['non-appearance points', 'over 75 mins', 'big chances created', 'big chances missed', 'minutes'], data=[[0, 0, 0, 0, 0]])
            print(data.columns.values)
            save_df(data, 'Data/players_pickle/' + str(counter) + '.pickle')

        counter += 1


def json_to_df(data):
    # Converting the main FPL data into a pickle file after being cleaned and shaped
    pd.set_option('display.max_colwidth', -1)
    file = open(data, 'r')
    fpl_data = json.load(file)
    fpl_data = pd.DataFrame(fpl_data['elements'])
    fpl_data = fpl_data.rename(columns={'element_type': 'position', 'now_cost': 'price',
                                        'selected_by_percent': 'ownership', 'bps': 'bonus points',
                                        'total_points': 'total points', 'first_name': 'first name',
                                        'second_name': 'second name'})

    for col in ['threat', 'creativity', 'points_per_game', 'ownership']:
        fpl_data[col] = fpl_data[col].astype(float)

    fpl_data['position'] = (fpl_data['position']).astype(str)
    fpl_data['minutes'] = (fpl_data['minutes']).astype(int)

    fpl_data = combining_dfs(fpl_data)
    fpl_data = calculate_value(fpl_data)
    fpl_data = positions(fpl_data)
    fpl_data = vapm(fpl_data)
    fpl_data = merge_names(fpl_data)
    fpl_data = form(fpl_data, 5)
    fpl_data = calculate_value(fpl_data)
    fpl_data = formatting(fpl_data)
    fpl_data = team_names(fpl_data, 'team')
    fpl_data = clean_df(fpl_data)
    fpl_data.to_pickle("Data/fpl.pickle")


def formatting(data):
    # Removing apostrophes from players names as N'Golo Kante was throwing an error
    data['Player Name'] = data['Player Name'].replace("'", "", regex=True)
    return data


def merge_names(data):
    # Merging the first and second name columns into one column
    data['Player Name'] = data['first name'] + ' ' + data['second name']
    return data


def vapm(data):
    # Calculating Value Added Per Million column
    data['VAPM'] = \
        np.where(data['position'] == 'Goalkeeper', (data['non-appearance points'] / data['minutes']) / (data['price'] - 35) * 10000,
                 np.where(data['position'] == 'Defender',
                          (data['non-appearance points'] / data['minutes']) / (data['price'] - 35) * 10000,
                          np.where(data['position'] == 'Midfielder',
                                   (data['non-appearance points'] / data['minutes']) / (data['price'] - 40) * 10000,
                                   np.where(data['position'] == 'Striker',
                                            (data['non-appearance points'] / data['minutes']) / (data['price'] - 40) * 10000, 0))))
    return data


def clean_df(fpl_data):
    # Cleaning the main FPL data and making it more readable
    fpl_data = fpl_data.round(2)
    fpl_data = fpl_data.fillna(0)

    return fpl_data


def calculate_value(data):
    # Calculating player value
    data['value'] = (data['total points'] / data['minutes']) / data['price'] * 10000
    data['non-appearance value'] = (data['non-appearance points'] / data['minutes']) / data['price'] * 10000
    data['NA-PP90'] = (data['non-appearance points'] / data['minutes']) * 90

    return data


def combining_dfs(data):
    # Combining the individual player data and the main fpl data
    counter = 1
    main_data = data

    for file_name in natsorted(os.listdir('Data/players_pickle')):
            data = load_df('Data/players_pickle/' + file_name)
            non_app_points = data['non-appearance points'].sum()
            seventy_five_mins = data['over 75 mins'].sum()
            big_chances_created = data['big chances created'].sum()
            big_chances_missed = data['big chances missed'].sum()
            main_data.loc[main_data['id'] == counter, 'non-appearance points'] = non_app_points
            main_data.loc[main_data['id'] == counter, 'over 75 mins'] = seventy_five_mins
            main_data.loc[main_data['id'] == counter, 'big chances created'] = big_chances_created
            main_data.loc[main_data['id'] == counter, 'big chances missed'] = big_chances_missed
            counter += 1

    return main_data


def form(data, num_of_matches):
    # Calculating form for the number of games specified by the user

    # Creating the headers for each column which will be dynamic dependent on user input
    non_appearance_header = 'Non-Appearance Points Last ' + str(num_of_matches) + ' Matches'
    mins_header = 'Mins Last ' + str(num_of_matches) + ' Matches'
    napp90_header = 'NAPP90 Last ' + str(num_of_matches) + ' Matches'

    # Iterating through each player and calculating their form which is non-appearance points, minutes played & non-apperance points per 90 minutes over the last x games
    counter = 1
    main_data = data
    for file_name in natsorted(os.listdir('Data/players_pickle')):
        data = load_df('Data/players_pickle/' + file_name)
        mins_last_x = data['minutes'][-int(num_of_matches):].sum()
        non_appearance_last_x = (data['non-appearance points'][-int(num_of_matches):].sum() / data['minutes'][-int(num_of_matches):].sum()) / main_data.loc[main_data['id'] == counter, 'price'] * 10000
        napp90_last_x = (data['non-appearance points'][-int(num_of_matches):].sum() / data['minutes'][-int(num_of_matches):].sum()) * 90

        main_data.loc[main_data['id'] == counter, napp90_header] = napp90_last_x
        main_data.loc[main_data['id'] == counter, non_appearance_header] = non_appearance_last_x
        main_data.loc[main_data['id'] == counter, mins_header] = mins_last_x
        counter += 1

    # Returning the data with the new headers
    main_data = main_data[['id', 'VAPM', 'Player Name', 'minutes', mins_header, 'price', 'total points', 'ownership',
                         'position', 'threat', 'creativity', 'team', non_appearance_header, 'non-appearance points',
                         'NA-PP90', napp90_header, 'over 75 mins', 'big chances created', 'big chances missed']]
    return main_data


def positions(data):
    # Changing element types to positions
    vals_to_replace = {'1': 'Goalkeeper', '2': 'Defender', '3': 'Midfielder', '4': 'Striker'}
    data['position'] = data['position'].map(vals_to_replace)

    return data


def team_names(data, name):
    # Converting the integers to team names
    data[name] = (data[name].replace([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
                                          14, 15, 16, 17, 18, 19, 20],
                                         ['Arsenal', 'Bournemouth', 'Brighton', 'Burnley', 'Cardiff',
                                          'Chelsea',
                                          'C Palace', 'Everton', 'Fulham', 'Huddersfield', 'Leicester',
                                          'Liverpool', 'Man City', 'Man Utd', 'Newcastle', 'Southampton',
                                          'Spurs', 'Watford', 'West Ham', 'Wolves']))

    return data


def run_data():
    # Functions required for code to run
    retrieve_data()
    get_players()
    clean_players()
    json_to_df('Data/fpl.json')
    print(load_df('Data/fpl.pickle'))


def save_df(data, filepath):
    data.to_pickle(filepath)


def load_df(filepath):
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return data


#    def print_pickle(pickle):
#    df = load_df(pickle)
#    writer = pd.ExcelWriter('C:/Users/Chappy/df.xlsx', engine='xlsxwriter')
#    df.to_excel(writer, index=False, sheet_name='report')
#    workbook = writer.book
#    worksheet = writer.sheets['report']
#    workbook.close()

run_data()

