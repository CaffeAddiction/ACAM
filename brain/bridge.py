import subprocess
import time
import os

def measure_execution(number_to_factor, algo_choice=1):
    """
    number_to_factor: Çarpanlarına ayrılacak sayı
    algo_choice: 1 (Pollard's Rho), 2 (Trial Division)
    """
    # Projenin kök dizinini ve exe yolunu bulur
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_path = os.path.join(base_dir, 'engine', 'factor.exe')
    
    start_time = time.perf_counter()
    
    try:
        # C++ motorunu çalıştır (GIRINTIYE DIKKAT: 8 bosluk iceride olmali)
        process = subprocess.run(
            [exe_path, str(number_to_factor), str(algo_choice)], 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        # Hata kontrolü
        if process.returncode != 0:
            return {"status": "error", "output": process.stderr}

        end_time = time.perf_counter()
        duration = end_time - start_time
        
        return {
            "number": number_to_factor,
            "bits": int(number_to_factor).bit_length(),
            "duration": duration,
            "output": process.stdout.strip(),
            "status": "success",
            "algo_used": "Pollard" if algo_choice == 1 else "TrialDivision"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Test: Pollard's Rho ile (1)
    print("Pollard Test:", measure_execution(10403, 1))
    # Test: Trial Division ile (2)
    print("Trial Test:", measure_execution(10403, 2))