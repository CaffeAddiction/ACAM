import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def plot_decision_boundary():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(base_dir, 'brain', 'acam_selector_model.pkl')
    model = joblib.load(model_path)

    # 10'dan 100'e kadar bit uzunlukları oluştur
    bit_range = np.arange(10, 101).reshape(-1, 1)
    df_range = pd.DataFrame(bit_range, columns=['bit_length'])
    decisions = model.predict(df_range)

    # Görselleştirme
    plt.figure(figsize=(10, 5))
    plt.step(bit_range, decisions, where='post', color='teal', linewidth=2)
    plt.yticks([1, 2], ['Pollard\'s Rho', 'Trial Division'])
    plt.xlabel('Bit Uzunluğu')
    plt.ylabel('AI Seçimi')
    plt.title('ACAM Algoritma Seçim Karar Sınırı')
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # Grafiği kaydet
    plt.savefig(os.path.join(base_dir, 'tests', 'decision_logic.png'))
    plt.show()

if __name__ == "__main__":
    plot_decision_boundary()