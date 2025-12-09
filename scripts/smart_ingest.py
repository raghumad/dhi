import os
import sys
import time
import signal
import subprocess
import glob
import multiprocessing

# --- Configuration ---
THERMAL_LIMIT_HIGH = 85000  # 85°C (in millidegrees)
THERMAL_LIMIT_LOW = 75000   # 75°C
CHECK_INTERVAL = 1.0        # Seconds

def get_cpu_temp():
    """
    Reads the highest temperature from /sys/class/thermal/thermal_zone*/temp.
    Returns temp in millidegrees Celsius.
    """
    max_temp = 0
    try:
        zones = glob.glob("/sys/class/thermal/thermal_zone*/temp")
        for zone in zones:
            with open(zone, "r") as f:
                try:
                    t = int(f.read().strip())
                    if t > max_temp:
                        max_temp = t
                except:
                    continue
    except Exception as e:
        print(f"Warning: Could not read thermal zones: {e}")
    return max_temp

def set_affinity(reserved_cores=2):
    """
    Sets affinity to use all CPUs except the last N (reserved).
    """
    try:
        cpu_count = multiprocessing.cpu_count()
        if cpu_count <= reserved_cores:
            print(f"Not enough cores to reserve {reserved_cores}. Using all.")
            return

        # Simple logic: Exclude the last 'reserved_cores' IDs
        # e.g., 64 cores -> Use 0-61. Reserve 62, 63.
        allowed = list(range(cpu_count - reserved_cores))
        
        # Apply to current process (children inherit it)
        os.sched_setaffinity(0, allowed)
        print(f"✅ Core Affinity Set: Using {len(allowed)}/{cpu_count} cores. (Reserved {reserved_cores} for system)")
    except Exception as e:
        print(f"Warning: Failed to set affinity: {e}")

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} [COMMAND]")
        sys.exit(1)

    cmd = sys.argv[1:]
    
    # 1. Set Affinity
    set_affinity(reserved_cores=4) # Reserve 4 cores on a desktop
    
    # 2. Start Process
    print(f"🚀 Launching constrained process: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd)
    
    paused = False

    try:
        while proc.poll() is None:
            # 3. Monitor Thermal
            current_temp = get_cpu_temp()
            
            # Simple Hysteresis Control
            if not paused and current_temp > THERMAL_LIMIT_HIGH:
                print(f"🔥 Temp {current_temp/1000:.1f}°C > Limit! Pausing ingestion...")
                proc.send_signal(signal.SIGSTOP)
                paused = True
                
            elif paused and current_temp < THERMAL_LIMIT_LOW:
                print(f"❄️ Temp {current_temp/1000:.1f}°C safe. Resuming...")
                proc.send_signal(signal.SIGCONT)
                paused = False
                
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping...")
        proc.terminate()
        
    print(f"Process finished with code {proc.returncode}")
    sys.exit(proc.returncode)

if __name__ == "__main__":
    main()
