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
import FitbitKeys

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
    #print(df.columns)
    #print(df.head())
    try:
        df["Time"] = pd.to_datetime(df["Time"])
    except KeyError:
        print("Sync your fitbit first!")
        sys.exit()
    except:
        print("Unexpected error: ", sys.exc_info()[0])
        raise
        sys.exit()
    
    #print(df.head())
    df = df.set_index("Time")
    #print(df.head())
    df = df.resample("5T").mean()
    #print(df.head())
    #for i in df["Time"]:
    #    print(i + "\n")
    return df

def noiseDataCollector():
    noise_data = requests.get("http://dublincitynoise.sonitussystems.com/applications/api/dublinnoisedata.php?location=8")
    noise = pd.DataFrame.from_dict(noise_data.json())
    noise["times"] = pd.to_datetime(noise['times'])
    return noise

def pushToCloud(dtype, data, db):
    jsonData = data.to_dict(orient = 'records')

    if dtype == "heart rate":
        time_df = data.index.to_frame()
        time_jsonData = time_df.to_dict(orient = 'records')
        doc_ref = db.collection(u'HeartRate_Data')
        for record, t_record in zip(jsonData, time_jsonData):
            doc_ref.add({
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

def generateData():
    print("generateData function to be built.")

def manipulateData():
    print("manipulateData function to be built.")

def visualization():
    print("visualization function to be built.")

def mainFunc(auth, db):
    while True:
        inp = input("Enter 1 -> Live HR | 2 -> Live Noise | 3 -> Generate data | 4 -> Manipulate data | 5 -> Visualize | 6 -> Exit : ")
        
        if inp == "1":
            hr = hrDataCollector(auth)
        
            #if hr.empty:
            #    pass
        
            #else:
            #    user = FitbitKeys.getFitbitClientID()
                #conn.execute("UPDATE User_endtime SET Time = ? WHERE Userkey = ?", (hr.iloc[-1]["Time"], user))
                #conn.commit()
            print("Attempting to push HR data to firestore.")
            pushToCloud("heart rate", hr, db)
            print("Heart rate data pushed to firestore.")

        elif inp == "2":
            noise = noiseDataCollector()
            print("Attempting to push Noise data to firestore.")
            pushToCloud("noise", noise, db)
            print("Noise data pushed to firestore.")
        
        elif inp == "3":
            generateData()

        elif inp == "4":
            manipulateData()

        elif inp == "5":
            visualization()

        elif inp == "6":
            sys.exit()

        else:
            pass

def setup():
    userKey = FitbitKeys.getFitbitClientID()
    userSecret = FitbitKeys.getFitbitClientSecret()
    auth = authorizer(userKey, userSecret)
    cred = credentials.Certificate("Firebase_SA_Key.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    #Setup is done. Now calling mainFunc to start the application.

    mainFunc(auth, db)

if __name__ == "__main__":
    setup()