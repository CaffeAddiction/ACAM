import sys, os, csv, random
from sympy import nextprime

# Root dizini yola ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from brain.bridge import measure_execution
from brain.analysis import extract_features

def collect_3way_data(samples=150): # Örnek sayısını 150 yaptım, daha iyi öğrenir
    csv_path = os.path.join(os.path.dirname(__file__), 'training_data.csv')
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['bit_length', 'dist_to_square', 'p_time', 't_time', 'f_time', 'winner'])
        
        print(f"--- ACAM 3-Way Fermat Odaklı Veri Toplama Başladı ---")
        
        for i in range(samples):
            bits = random.randint(16, 60)
            
            # %40 İhtimalle Fermat vakası (birbirine yakın p ve q)
            if random.random() < 0.4:
                p = nextprime(random.getrandbits(bits // 2))
                q = nextprime(p + random.randint(2, 500)) # Araları çok yakın
            else:
                # Normal vaka (rastgele p ve q)
                p = nextprime(random.getrandbits(bits // 2))
                q = nextprime(random.getrandbits(bits // 2))
                
            n = p * q
            
            feat = extract_features(n)
            res_p = measure_execution(n, 1) # Pollard
            res_t = measure_execution(n, 2) # Trial
            res_f = measure_execution(n, 3) # Fermat
            
            times = [res_p['duration'], res_t['duration'], res_f['duration']]
            winner = times.index(min(times)) + 1
            
            writer.writerow([feat['bit_length'], feat['dist_to_square'], times[0], times[1], times[2], winner])
            print(f"[{i+1}] Bit: {feat['bit_length']} | Kazanan: {winner}")

if __name__ == "__main__":
    collect_3way_data(150)