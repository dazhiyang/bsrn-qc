"""
BSRN Data Retrieval Module.
Handles FTP connections and automated downloads.
"""

from ftplib import FTP
import os

def get_bsrn_file_inventory(stations: list, username, password, host="ftp.bsrn.awi.de"):
    """
    Connects to BSRN FTP and lists available station-to-archive files.
    
    Returns:
        dict: {STN: [list of filenames]}
    """
    inventory = {}
    try:
        with FTP(host) as ftp:
            ftp.set_pasv(True)
            ftp.login(user=username, passwd=password)
            
            for stn in stations:
                stn_lower = stn.lower()
                success = False
                
                # Try retrieval with a retry logic for the connection
                for attempt in range(2):
                    try:
                        ftp.cwd("/")
                        try:
                            ftp.cwd(stn_lower)
                        except:
                            ftp.cwd(stn_lower.upper())
                        
                        inventory[stn.upper()] = ftp.nlst()
                        success = True
                        break
                    except Exception as e:
                        if attempt == 0:
                            # Transient connection drop, attempt relogin
                            try:
                                ftp.connect(host)
                                ftp.login(user=username, passwd=password)
                                ftp.set_pasv(True)
                            except:
                                pass
                        else:
                            print(f"BSRN FTP: Failed to retrieve {stn} after retry: {e}")
                
                if not success:
                    inventory[stn.upper()] = []
                    
    except Exception as e:
        print(f"BSRN FTP: Major Connection Error: {e}")
    return inventory

def download_bsrn_file(remote_path, local_dir, username, password, host="ftp.bsrn.awi.de"):
    """
    Downloads a single file from BSRN FTP.
    """
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, os.path.basename(remote_path))
    
    try:
        with FTP(host) as ftp:
            ftp.set_pasv(True)
            ftp.login(user=username, passwd=password)
            with open(local_path, "wb") as f:
                ftp.retrbinary(f"RETR {remote_path}", f.write)
        return local_path
    except Exception as e:
        print(f"Download Error for {remote_path}: {e}")
        return None
