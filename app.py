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
    with open('C:/Users/Chappy/PycharmProjects/FPL_Website/Data/2019-20/fpl.pickle', 'rb') as f:
        data = pickle.load(f)
    return render_template('index.html', data=data.to_html(escape=False, index=False, classes='my_class" id = "fpl'))


@app.route('/', methods=["GET", "POST"])
def teams():
    if request.method == "POST":
        with open('C:/Users/Chappy/PycharmProjects/FPL_Website/Data/2019-20/fpl.pickle', 'rb') as f:
            data = pickle.load(f)
        new_data = form(data, request.form['last-x-games'])
        new_data = clean_df(new_data)
        return render_template('index.html',
                               data=new_data.to_html(escape=False, index=False, classes='my_class" id = "fpl'))


@app.route('/player/<number>')
def player(number):
    data = load_df('Data/players_pickle/1.pickle')
    print(number)
    return render_template('player.html', data=data.to_html(escape=False))


# if __name__ == '__main__':
#    app.run()


def retrieve_data():
    # Pulling the data from the FPL website
    fpl_data = requests.get('https://fantasy.premierleague.com/api/bootstrap-static/').json()
    with open('Data/2019-20/fpl.json', 'w') as f:
        json.dump(fpl_data, f)


def player_total(data):
    # Returns the number of players in the data
    num_of_players = (len(data))
    return num_of_players


def player_urls(total):
    # Creates a list containing the url for each player
    player_link = 'https://fantasy.premierleague.com/api/element-summary/'
    url_list = []

    for i in range(1, total + 1):
        player_address = player_link + str(i) + '/'
        url_list.append(player_address)

    return url_list


def get_players():
    # Iterates through the player url list and saves a copy of each player's data as a json file
    counter = 1
    for player in player_urls(player_total(load_df('Data/2019-20/fpl.pickle'))):
        data = requests.get(player).json()
        print(counter)
        with open('Data/2019-20/players/' + str(counter) + '.json', 'w') as f:
            json.dump(data, f)
        counter += 1


def clean_players():
    # Shaping the player data and saving as a pickle
    counter = 1
    for file_name in natsorted(os.listdir('Data/2019-20/players')):
        file = open('Data/2019-20/players/' + file_name, 'r')
        data = json.load(file)
        try:
            data = pd.DataFrame(data['history'])
            data = data.rename(
                columns={'opponent_team': 'opponent', 'was_home': 'was home', 'total_points': 'total points'})
            data.columns = data.columns.str.title()
            # Creating a column for non-appearance points
            for index, row in data.iterrows():
                if row['Minutes'] > 59:
                    data.loc[index, 'Non-Appearance Points'] = row['Total Points'] - 2
                elif row['Minutes'] > 0:
                    data.loc[index, 'Non-Appearance Points'] = row['Total Points'] - 1
                else:
                    data.loc[index, 'Non-Appearance Points'] = 0
            # Saving the data required. Also preventing an error that is thrown when a new player to the Premier League has no data
            if not data.empty:
                data = data[['Non-Appearance Points', 'Minutes']]
                data.to_pickle('Data/2019-20/players_pickle/{}.pickle'.format(counter))
            else:
                data = pd.DataFrame(columns=['Non-Appearance Points', 'Minutes'], data=[[0, 0]])
                data.to_pickle('Data/2019-20/players_pickle/{}.pickle'.format(counter))
        except KeyError:
            data = pd.DataFrame(columns=['Non-Appearance Points', 'Minutes'], data=[[0, 0]])
            data.to_pickle('Data/2019-20/players_pickle/{}.pickle'.format(counter))
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

    fpl_data.columns = fpl_data.columns.str.title()

    for col in ['Threat', 'Creativity', 'Points_Per_Game', 'Ownership']:
        fpl_data[col] = fpl_data[col].astype(float)

    fpl_data['Position'] = (fpl_data['Position']).astype(str)
    fpl_data['Minutes'] = (fpl_data['Minutes']).astype(int)

    fpl_data = combining_dfs(fpl_data)
    fpl_data = positions(fpl_data)
    fpl_data = calculate_value(fpl_data)
    fpl_data = vapm(fpl_data)
    fpl_data = merge_names(fpl_data)
    fpl_data = form(fpl_data, 5)
    fpl_data = formatting(fpl_data)
    fpl_data = team_names(fpl_data)
    fpl_data = clean_df(fpl_data)
    fpl_data = rename_columns(fpl_data)

    fpl_data.to_pickle("Data/2019-20/fpl.pickle")


def formatting(data):
    # Removing apostrophes from players names as N'Golo Kante was throwing an error
    data['Player Name'] = data['Player Name'].replace("'", "", regex=True)
    return data


def rename_columns(data):
    data.columns = data.columns.str.title()
    data = data.rename(columns={'Vapm': 'VAPM', 'Napp/90': 'NAPP/90',
                       'Threat': 'Threat/90', 'Creativity': 'Creativity/90'})
    return data


def merge_names(data):
    # Merging the first and second name columns into one column
    data['Player Name'] = data['First Name'] + ' ' + data['Second Name']
    return data


def vapm(data):
    # Calculating Value Added Per Million column
    data['VAPM'] = \
        np.where(data['Position'] == 'Goalkeeper',
                 (data['Non-Appearance Points'] / data['Minutes']) / (data['Price'] - 35) * 10000,
                 np.where(data['Position'] == 'Defender',
                          (data['Non-Appearance Points'] / data['Minutes']) / (data['Price'] - 35) * 10000,
                          np.where(data['Position'] == 'Midfielder',
                                   (data['Non-Appearance Points'] / data['Minutes']) / (data['Price'] - 40) * 10000,
                                   np.where(data['Position'] == 'Striker',
                                            (data['Non-Appearance Points'] / data['Minutes']) / (
                                                    data['Price'] - 40) * 10000, 0))))
    return data


def clean_df(fpl_data):
    # Cleaning the main FPL data and making it more readable
    fpl_data = (fpl_data.round(2)
                .fillna(0))

    return fpl_data


def calculate_value(data):
    # Calculating player value
    data['NAPP/90'] = (data['Non-Appearance Points'] / data['Minutes']) * 90
    data['Threat/90'] = (data['Threat'] / data['Minutes']) * 90
    data['Creativity/90'] = (data['Creativity'] / data['Minutes']) * 90

    return data


def combining_dfs(data):
    # Combining the individual player data and the main fpl data
    counter = 1
    main_data = data

    for file_name in natsorted(os.listdir('Data/2019-20/players_pickle')):
        data = load_df('Data/2019-20/players_pickle/' + file_name)
        non_app_points = data['Non-Appearance Points'].sum()
        main_data.loc[main_data['Id'] == counter, 'Non-Appearance Points'] = non_app_points
        counter += 1

    return main_data


def form(data, num_of_matches):
    # Calculating form for the number of games specified by the user

    # Creating the headers for each column which will be dynamic dependent on user input
    non_appearance_header = 'Non-Appearance Points Last {} Matches'.format(num_of_matches)
    mins_header = 'Mins Last {} Matches'.format(num_of_matches)
    napp90_header = 'NAPP/90 Last {} Matches'.format(num_of_matches)

    # Iterating through each player and calculating their form which is non-appearance points, minutes played & non-apperance points per 90 minutes over the last x games
    counter = 1
    main_data = data
    for file_name in natsorted(os.listdir('Data/2019-20/players_pickle')):
        data = load_df('Data/2019-20/players_pickle/' + file_name)

        mins_last_x = data['Minutes'][-int(num_of_matches):].sum()
        non_appearance_last_x = data['Non-Appearance Points'][-int(num_of_matches):].sum()
        napp90_last_x = (data['Non-Appearance Points'][-int(num_of_matches):].sum() / data['Minutes'][-int(num_of_matches):].sum()) * 90

        main_data.loc[main_data['Id'] == counter, napp90_header] = napp90_last_x
        main_data.loc[main_data['Id'] == counter, non_appearance_header] = non_appearance_last_x
        main_data.loc[main_data['Id'] == counter, mins_header] = mins_last_x
        print(file_name)
        counter += 1

    # Returning the data with the new headers
    main_data = main_data[['Id', 'Price', 'Player Name', 'Position', 'Team', 'VAPM', 'NAPP/90', 'Minutes',
                           'Total Points', 'Non-Appearance Points',
                           'Ownership', 'Threat/90', 'Creativity/90', mins_header, non_appearance_header,
                           napp90_header]]
    return main_data


def positions(data):
    # Changing element types to positions
    vals_to_replace = {'1': 'Goalkeeper', '2': 'Defender', '3': 'Midfielder', '4': 'Striker'}
    data['Position'] = data['Position'].map(vals_to_replace)

    return data


def team_names(data):
    # Converting the integers to team names
    data['Team'] = (data['Team'].replace([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
                                          14, 15, 16, 17, 18, 19, 20],
                                         ['Arsenal', 'Aston Villa', 'Bournemouth', 'Brighton', 'Burnley',
                                          'Chelsea', 'C Palace', 'Everton', 'Leicester', 'Liverpool', 'Man City',
                                          'Man Utd', 'Newcastle', 'Norwich', 'Sheff Utd', 'Southampton',
                                          'Spurs', 'Watford', 'West Ham', 'Wolves']))

    return data


def run_data():
    # Functions required for code to run
    retrieve_data()
    get_players()
    clean_players()
    json_to_df('Data/2019-20/fpl.json')


def save_df(data, filepath):
    data.to_pickle(filepath)


def load_df(filepath):
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return data


run_data()
