import fitbit
from fitbit import gather_keys_oauth2 as Oauth2
import pandas as pd 
import numpy as np
import datetime
from datetime import timedelta
import sys
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json
import requests
import time
import Keys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import Emailer
import os

def authorizer(userKey, userSecret):
    server = Oauth2.OAuth2Server(userKey, userSecret)
    server.browser_authorize()
    accessToken = str(server.fitbit.client.session.token['access_token'])
    refreshToken = str(server.fitbit.client.session.token['refresh_token'])
    authd_client = fitbit.Fitbit(client_id = userKey, client_secret = userSecret, access_token = accessToken, refresh_token = refreshToken, system='en_GB')
    return authd_client

def hrDataCollector(auth):
    heartRate = auth.intraday_time_series(resource = "activities/heart", base_date = 'today', detail_level = '1min', start_time = None, end_time = None)
    df = pd.DataFrame(heartRate["activities-heart-intraday"]["dataset"])
    df = df.rename(columns = {"time": "Time", "value": "Heart rate [BPM]"})
    
    try:
        df["Time"] = pd.to_datetime(df["Time"])
    except KeyError:
        print("Sync your fitbit first!")
        return None
    except:
        print("Unexpected error: ", sys.exc_info()[0])
        raise
        sys.exit()
    
    df = df.set_index("Time")
    df = df.resample("5T").mean()
    return df

def noiseDataCollector():
    noise_data = requests.get("http://dublincitynoise.sonitussystems.com/applications/api/dublinnoisedata.php?location=8")
    noise = pd.DataFrame.from_dict(noise_data.json())
    noise["times"] = pd.to_datetime(noise['times'])
    return noise

def pushToCloud(dtype, data, db, user = None):
    jsonData = data.to_dict(orient = 'records')

    if dtype == "heart rate":
        time_df = data.index.to_frame()
        time_jsonData = time_df.to_dict(orient = 'records')
        user_a_ref = db.collection(u'Users').document(user)
        HeartRateData_ref = user_a_ref.collection(u'HeartRateData')
        for record, t_record in zip(jsonData, time_jsonData):
            HeartRateData_ref.add({
                u'Time': t_record["Time"],
                u'Heart rate [BPM]': record["Heart rate [BPM]"],
            })
    else:
        doc_ref = db.collection(u'Open_Noise_Data')
        for record in jsonData:
            doc_ref.add({
                u'Time': record["times"],
                u'aleq': record["aleq"],
            })

def actuation(auth):
    hrList = []
    for i in range(1,6):
        hrFile = pd.read_csv("Generated_Data/HR/heart_rate_{}.csv".format(i))
        hrFile = instanceDataPreProcessing(hrFile)
        hrList.append(hrFile.iloc[-1]["Heart rate [BPM]"])

    hr = np.array(hrList)

    if hr.mean() > 70:
        print("Sending an email to notify authorities about the potential disaster.")
        Emailer.sendEmail()
        print("Check the graph to see why the trigger was set off.")
        visualization(auth)
    else:
        print("No mandatory action required. Check the graph out if you want.")
        visualization(auth)

def visualization(auth):

    #Pulling HR Data
    hrList = []
    for i in range(1,6):
        hr = pd.read_csv("Generated_Data/HR/heart_rate_{}.csv".format(i))
        hr = instanceDataPreProcessing(hr)
        hrList.append(hr)
    
    hr_concat = pd.concat((hrList[0], hrList[1], hrList[2], hrList[3], hrList[4]))
    temp = hr_concat.groupby(hr_concat.index)
    hr_means = temp.mean()
    
    #Pulling noise data

    noise = noiseDataCollector()
    noise = noise.astype({'aleq': 'float64'})

    ax = hr_means.plot(kind = "bar", width = 0.1)
    noise['aleq'].plot(color = 'red', secondary_y = True, xlim = ax.get_xlim())
    plt.xlabel('Time')
    ax.set_ylabel('Heart Rate')
    plt.ylabel('A-weighted Equivalent Level (Noise values)')
    plt.show()

def instanceDataPreProcessing(hr):
    hr["Time"] = pd.to_datetime(hr["Time"])
    hr = hr.set_index("Time")
    return hr

def otherInstances(db):
    print("Attempting to push emulated data from other sensor instances.")
    for i in range(2,6):
        hr = pd.read_csv("Generated_Data/HR/heart_rate_{}.csv".format(i))
        hr = instanceDataPreProcessing(hr)
        pushToCloud("heart rate", hr, db, "Instance-{}".format(i))
        print("Pushed instance-{} of emulated heart rate sensor data".format(i))
    print("Done pushing emulated heart rate sensor data to firestore.")

def mainFunc(auth, db):
    while True:

        hr = hrDataCollector(auth)
        #hr = None
        if hr.empty:
            print("Attempting to push emulated data to firestore.")
            hr = pd.read_csv("Generated_Data/HR/heart_rate_1.csv")
            hr = instanceDataPreProcessing(hr)
            pushToCloud("heart rate", hr, db, "Instance-1")
            print("Pushed emulated sensor-1 data.")
            otherInstances(db)          

        else:
            print("Attempting to pull live HR Data and pushing it to firestore.")
            user = Keys.getFitbitClientID()
            pushToCloud("heart rate", hr, db, user)
            pwd = os.getcwd()
            os.chdir(pwd+'/Generated_Data/HR/')
            hr.to_csv('heart_rate_1.csv')
            os.chdir("../")
            os.chdir("../")
            print("Live heart rate data from sensor-1 pushed to firestore.")
            otherInstances(db)

        print("Pulling live noise data now.")
        noise = noiseDataCollector()
        print("Attempting to push live noise data to firestore.")
        pushToCloud("noise", noise, db)
        print("Noise data pushed to firestore.")
        if float(noise.iloc[-1]["aleq"]) > 50:
            actuation(auth)
        else:
            pass

        print("Press 'Ctrl+C' if you want to exit the program now.")
        time.sleep(10)


def setup():
    userKey = Keys.getFitbitClientID()
    userSecret = Keys.getFitbitClientSecret()
    auth = authorizer(userKey, userSecret)
    cred = credentials.Certificate("Firebase_SA_Key.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    #Setup is done. Now calling mainFunc to start the application.

    mainFunc(auth, db)

if __name__ == "__main__":
    setup()