import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib, os

def train_selector():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, 'data', 'training_data.csv')
    model_path = os.path.join(base_dir, 'brain', 'acam_selector.pkl')
    
    df = pd.read_csv(data_path)
    # Modeli iki kritere göre eğit: Uzunluk ve Kareye Yakınlık
    X = df[['bit_length', 'dist_to_square']]
    y = df['winner']
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    joblib.dump(model, model_path)
    print("--- 3 Algoritmalı ACAM Seçici Eğitildi ---")

if __name__ == "__main__":
    train_selector()