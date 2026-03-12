"""
BSRN Data Retrieval Module.
Handles FTP connections and automated downloads.
BSRN 数据获取模块。
处理 FTP 连接和自动下载。
"""

from ftplib import FTP
import os

def get_bsrn_file_inventory(stations, username, password, host="ftp.bsrn.awi.de"):
    """
    Connects to BSRN FTP and lists available station-to-archive files.
    连接到 BSRN FTP 并列出可用的站点存档文件。

    Parameters
    ----------
    stations : list
        List of station abbreviations (e.g., ['PAY', 'NYA']).
        站点缩写列表（例如 ['PAY', 'NYA']）。
    username : str
        BSRN FTP username.
        BSRN FTP 用户名。
    password : str
        BSRN FTP password.
        BSRN FTP 密码。
    host : str, default "ftp.bsrn.awi.de"
        FTP host address.
        FTP 主机地址。

    Returns
    -------
    inventory : dict
        Mapping of station abbreviations to lists of filenames.
        站点缩写到文件名列表的映射。
    """
    inventory = {}
    try:
        with FTP(host) as ftp:
            ftp.set_pasv(True)
            ftp.login(user=username, passwd=password)
            
            for stn in stations:
                stn_lower = stn.lower()
                success = False
                
                # Retry logic for the connection / 连接重试逻辑
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
                            # Re-establish connection on failure / 失败时重新建立连接
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
    从 BSRN FTP 下载单个文件。

    Parameters
    ----------
    remote_path : str
        The path to the file on the FTP server.
        FTP 服务器上的文件路径。
    local_dir : str
        The local directory to save the file.
        保存文件的本地目录。
    username : str
        BSRN FTP username.
        BSRN FTP 用户名。
    password : str
        BSRN FTP password.
        BSRN FTP 密码。
    host : str, default "ftp.bsrn.awi.de"
        FTP host address.
        FTP 主机地址。

    Returns
    -------
    local_path : str or None
        The path to the downloaded file, or None if failed.
        下载文件的路径，如果失败则返回 None。
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
