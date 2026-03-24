import subprocess
import os
import time

def run_script(script_path, log_file):
    msg = f"\n--- Running {script_path} ---\n"
    print(msg.strip())
    log_file.write(msg)
    log_file.flush() # Ensure msg is written immediately
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        # Pass log_file directly as stdout/stderr for real-time writing
        # -u means unbuffered output
        process = subprocess.run(["python", "-u", script_path], stdout=log_file, stderr=log_file, env=env)
        return process.returncode == 0
    except Exception as e:
        err_msg = f"Failed to run {script_path}: {e}\n"
        print(err_msg.strip())
        log_file.write(err_msg)
        return False

def main():
    crawler_dir = "crawlers"
    crawlers = [
        "juice23.py", "juice24.py", "juice99.py", "modu.py",
        "vapemonster.py", "juicebox.py", "siasiu.py", "vape9.py", "tjf.py"
    ]
    
    start_time = time.time()
    success_count = 0
    
    with open("crawl_log.txt", "w", encoding="utf-8") as log_file:
        for crawler in crawlers:
            path = os.path.join(crawler_dir, crawler)
            if os.path.exists(path):
                if run_script(path, log_file):
                    success_count += 1
            else:
                msg = f"⚠️  Crawler file not found: {path}\n"
                print(msg.strip())
                log_file.write(msg)

    end_time = time.time()
    duration = (end_time - start_time) / 60
    
    print("\n" + "="*30)
    print(f"Crawling Job Finished!")
    print(f"Total Success: {success_count}/{len(crawlers)}")
    print(f"Total Duration: {duration:.2f} minutes")
    print("="*30)

if __name__ == "__main__":
    main()
