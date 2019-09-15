import pandas as pd
import requests
import json
import pickle
from natsort import natsorted
import numpy as np

data = pickle.load(open('Data/2018-19/fpl.pickle', 'rb'))
print(data)