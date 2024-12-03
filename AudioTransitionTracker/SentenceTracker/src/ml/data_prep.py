import json
import os
import numpy as np
import librosa

from utils import load_json_files
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

def generate_spectrogram_array(item):
    json_filename = item["name"]
    
    directory = "../../data/lectures_segments/json"
    filepath = f"{directory}/{json_filename}.json"
    
    print(f"Reading JSON from: {filepath}")
    
    audio_filepath = f"../../data/audio_files/audio_{json_filename.split('_')[0]}.mp3"
    
    with open(filepath, 'r') as file:
        data = json.load(file)
    
    start_time = data["start_time"]
    duration = data["duration"]
    if start_time > 1000 or duration > 1000:
        start_time /= 1000
        duration /= 1000

    print(f"start time is {start_time} and duration is {duration}")
    y, sr = librosa.load(audio_filepath)

    if not data["is_full"]: #usually the case
        start_sample = int(start_time * sr)
        end_sample = int((start_time + duration) * sr)
        if end_sample > len(y):
            end_sample = len(y)
        y = y[start_sample:end_sample]
        # self.duration = duration
    else:
        print("AudioLecture object is full, try again")
        exit()

    D = librosa.stft(y)
    S_db = librosa.amplitude_to_db(abs(D), ref=np.max)

    return S_db.T

def extract_features_and_labels(data):
    X = []
    y = []
    
    for item in data:
        spectrogram_data = generate_spectrogram_array(item)
        X.append(spectrogram_data)
        
        # Create label: 1 if full stop exists within segment, 0 otherwise
        has_fullstop = any(item['start_time'] <= ts < (item['start_time'] + item['duration'])
                           for ts in item['fullstop_timestamps'])
        y.append(1 if has_fullstop else 0)
    
    return np.array(X), np.array(y)

def save_datasets(X_train, X_test, y_train, y_test):
    np.savez('audio_data_train.npz', X_train=X_train, y_train=y_train)
    np.savez('audio_data_test.npz', X_test=X_test, y_test=y_test)
    print("Datasets saved successfully!")

if __name__ == "__main__":
    json_dir = "../../data/lectures_segments/json"
    json_data = load_json_files(json_dir)
    X, y = extract_features_and_labels(json_data)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    save_datasets(X_train, X_test, y_train, y_test)
    

'''
if __name__ == "__main__":
    json_file = input("INPUT JSON FILE: ")
    spectrogram = generate_spectrogram_no_image(json_file)
    print(f"Spectrogram: {spectrogram}")
    print(f"Spectrogram shape: {spectrogram.shape}")
'''