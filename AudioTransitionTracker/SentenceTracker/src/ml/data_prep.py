import json
import os
import os.path
import numpy as np
import librosa
import sys
from sklearn.model_selection import train_test_split
from utils import load_json_files

def animate_loading_bar(total, curr, bar_length=60):
    percentage = curr / total
    filled_length = int(bar_length * percentage)
    bar = '#' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f"\r|{bar}| {100 * percentage:.2f}% ")
    sys.stdout.flush()

def pad_or_truncate_spectrogram(S, target_shape=(216, 1025)):
    target_rows, target_cols = target_shape
    if S.shape[0] < target_rows:
        padding_rows = target_rows - S.shape[0]
        S = np.pad(S, ((0, padding_rows), (0, 0)), mode='constant')
    elif S.shape[0] > target_rows:
        S = S[:target_rows, :]
    if S.shape[1] < target_cols:
        padding_cols = target_cols - S.shape[1]
        S = np.pad(S, ((0, 0), (0, padding_cols)), mode='constant')
    elif S.shape[1] > target_cols:
        S = S[:, :target_cols]
    return S

def generate_spectrogram_array(audio_filepath, start_time, duration, is_full):
    y, sr = librosa.load(audio_filepath)
    if not is_full:
        start_sample = int(start_time * sr)
        end_sample = int((start_time + duration) * sr)
        y = y[start_sample:end_sample]
    D = librosa.stft(y)
    S_db = librosa.amplitude_to_db(abs(D), ref=np.max)
    return S_db.T

def get_surrounding_segments(item, data, spectrogram_dir):
    """Fetches spectrograms for the preceding, current, and succeeding segments."""
    video_id, start_time, end_time = item['name'].split('_')
    start_time = int(start_time)
    end_time = int(end_time)

    def load_spectrogram(video_id, start, end):
        filepath = os.path.join(spectrogram_dir, f"{video_id}_{start}_{end}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r') as file:
                data = json.load(file)
            return pad_or_truncate_spectrogram(generate_spectrogram_array(
                audio_filepath=f"../../data/audio_files/audio_{video_id}.mp3",
                start_time=data["start_time"],
                duration=data["duration"],
                is_full=data["is_full"]
            ))
        else:
            return np.zeros((216, 1025))  # Zero padding for missing segments

    # check if preceding prev spectrogram exists
    
    preceding = load_spectrogram(video_id, start_time - 5000, end_time - 5000)
    current = load_spectrogram(video_id, start_time, end_time)
    succeeding = load_spectrogram(video_id, start_time + 5000, end_time + 5000)

    return np.concatenate([preceding, current, succeeding], axis=0)  # Shape: (648, 1025)

def extract_features_and_labels(data, checkpoint_path="checkpoint.npz"):
    if os.path.exists(checkpoint_path):
        checkpoint = np.load(checkpoint_path)
        X = checkpoint["X"].tolist()
        y = checkpoint["y"].tolist()
        start_index = checkpoint["start_index"].item()
        print(f"Resuming from checkpoint: {start_index}/{len(data)}")
    else:
        X = []
        y = []
        start_index = 0

    for i, item in enumerate(data[start_index:], start=start_index):
        print(f"Processing item {i + 1}/{len(data)}: {item['name']}")
        try:
            extended_spectrogram = get_surrounding_segments(item, data, "../../data/lectures_segments/json")
            X.append(extended_spectrogram[..., np.newaxis])  # Add channel dimension
            
            # Label only for the middle segment
            has_fullstop = any(
                item['start_time'] <= ts < (item['start_time'] + item['duration'])
                for ts in item['fullstop_timestamps']
            )
            y.append(1 if has_fullstop else 0)

            # Save checkpoint
            np.savez(checkpoint_path, X=np.array(X), y=np.array(y), start_index=i + 1)
            animate_loading_bar(len(data), i + 1)
        except Exception as e:
            print(f"Error processing {item['name']}: {e}")

    return np.array(X), np.array(y)

if __name__ == "__main__":
    json_dir = "../../data/lectures_segments/json"
    json_data = load_json_files(json_dir)
    print(f"Total data: {len(json_data)}")
    X, y = extract_features_and_labels(json_data)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    np.savez('../../data/npz/fullstop_prediction_train.npz', X_train=X_train, y_train=y_train)
    np.savez('../../data/npz/fullstop_prediction_test.npz', X_test=X_test, y_test=y_test)
    print("Datasets saved successfully!")
