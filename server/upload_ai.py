import logging
import json
import os
import requests
import time
from pathlib import Path
from typing import Optional, List, Tuple

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s", 
    handlers=[logging.StreamHandler()]
)

def login_and_get_token(server_url: str, password: str) -> Optional[str]: 
    try: 
        response = requests.post(
            "{}/login".format(server_url), 
            json={"password": password}, 
            timeout=10
        )

        if response.status_code != 200: 
            logging.error("Login failed: %s", response.text)
            return None

        token = response.json().get("access_token")  # ✅ 修复：使用圆括号
        if not token: 
            logging.error("No access token in response: %s", response.json())
            return None

        return token
    except requests.exceptions.RequestException as e: 
        logging.error("Login request failed: %s", e)
        return None

def upload_folder_transactional(
    folder_path: str, 
    server_url: str, 
    password: str, 
    max_files: Optional[int] = None
) -> dict:
    """
    事务性上传文件夹：
    - 所有文件要么全部成功，要么全部失败
    - 使用 /secure-upload-folder 接口
    """
    folderpath = Path(folder_path)
    if not folderpath.exists(): 
        logging.error("Folder does not exist: %s", folderpath)
        return {"success": 0, "failed": 0, "total": 0}

    # 获取 Token
    token = login_and_get_token(server_url, password)
    if not token: 
        logging.error("Failed to get access token")
        return {"success": 0, "failed": 0, "total": 0}

    headers = {"Authorization": f"Bearer {token}"}
    
    # 收集所有文件
    files_to_upload = []
    for file_path in folderpath.rglob("*"):
        if file_path.is_file():
            relative_path = str(file_path.relative_to(folderpath))
            files_to_upload.append((str(file_path), relative_path))
    
    total = len(files_to_upload)
    if max_files:
        files_to_upload = files_to_upload[:max_files]
        total = len(files_to_upload)
    
    if total == 0:
        logging.warning("No files to upload")
        return {"success": 0, "failed": 0, "total": 0}
    
    logging.info("Preparing to upload %d files transactionally...", total)
    
    # 使用 multipart/form-data 发送所有文件
    try:
        files_data = []
        for file_path, relative_path in files_to_upload:
            files_data.append(("files", (relative_path, open(file_path, "rb"))))
        
        response = requests.post(
            f"{server_url}/secure-upload-folder",
            files=files_data,
            headers=headers,
            timeout=120  # 给更多时间处理大文件
        )
        
        # 关闭所有文件句柄
        for _, (_, file_obj) in files_data:
            file_obj.close()
        
        if response.status_code == 200:
            result = response.json()
            logging.info("✅ All %d files uploaded successfully", total)
            return {
                "success": total,
                "failed": 0,
                "total": total,
                "details": result
            }
        else:
            logging.error("❌ Transaction upload failed: %s", response.text)
            return {
                "success": 0,
                "failed": total,
                "total": total,
                "error": response.text
            }
            
    except requests.exceptions.RequestException as e:
        logging.error("❌ Upload request failed: %s", e)
        # 关闭所有文件句柄（清理）
        return {
            "success": 0,
            "failed": total,
            "total": total,
            "error": str(e)
        }

def upload_folder_force(
    folder_path: str, 
    server_url: str, 
    password: str, 
    max_files: Optional[int] = None
) -> dict:
    """
    强制上传模式（非事务性）
    - 单个文件失败不影响其他文件
    - 使用 /secure-upload-folder-force 接口
    """
    folderpath = Path(folder_path)
    if not folderpath.exists(): 
        logging.error("Folder does not exist: %s", folderpath)
        return {"success": 0, "failed": 0, "total": 0}

    token = login_and_get_token(server_url, password)
    if not token: 
        logging.error("Failed to get access token")
        return {"success": 0, "failed": 0, "total": 0}

    headers = {"Authorization": f"Bearer {token}"}
    
    # 收集文件
    files_data = []
    for file_path in folderpath.rglob("*"):
        if file_path.is_file():
            relative_path = str(file_path.relative_to(folderpath))
            files_data.append(("files", (relative_path, open(file_path, "rb"))))
    
    total = len(files_data)
    if max_files:
        files_data = files_data[:max_files]
        total = len(files_data)
    
    if total == 0:
        return {"success": 0, "failed": 0, "total": 0}
    
    logging.info("Uploading %d files (non-transactional)...", total)
    
    try:
        response = requests.post(
            f"{server_url}/secure-upload-folder-force",
            files=files_data,
            headers=headers,
            timeout=120
        )
        
        # 关闭文件句柄
        for _, (_, file_obj) in files_data:
            file_obj.close()
        
        if response.status_code == 200:
            result = response.json()
            success = result.get("uploaded", [])
            failed = result.get("failed", [])
            logging.info(
                "✅ Upload complete: %d success, %d failed",
                len(success), len(failed)
            )
            return {
                "success": len(success),
                "failed": len(failed),
                "total": total,
                "details": result
            }
        else:
            logging.error("Upload failed: %s", response.text)
            return {"success": 0, "failed": total, "total": total}
            
    except Exception as e:
        logging.error("Upload error: %s", e)
        return {"success": 0, "failed": total, "total": total}

def upload_folder_single_files(
    folder_path: str, 
    server_url: str, 
    password: str, 
    max_files: Optional[int] = None,
    retry_count: int = 3
) -> dict:
    """
    逐个文件上传（最稳妥，适合大文件或网络不稳定）
    """
    folderpath = Path(folder_path)
    if not folderpath.exists(): 
        logging.error("Folder does not exist: %s", folderpath)
        return {"success": 0, "failed": 0, "total": 0}

    token = login_and_get_token(server_url, password)
    if not token: 
        logging.error("Failed to get access token")
        return {"success": 0, "failed": 0, "total": 0}

    success_count = 0
    fail_count = 0
    total = 0

    files_to_upload = []
    for file_path in folderpath.rglob("*"):
        if file_path.is_file():
            relative_path = str(file_path.relative_to(folderpath))
            files_to_upload.append((str(file_path), relative_path))

    total = len(files_to_upload)
    if max_files: 
        files_to_upload = files_to_upload[:max_files]
        total = len(files_to_upload)

    logging.info("Starting upload of %d files one by one...", total)

    for idx, (file_path, relative_path) in enumerate(files_to_upload, 1): 
        logging.info("[%d/%d] Uploading: %s", idx, total, relative_path)

        # 使用单文件上传接口
        headers = {"Authorization": f"Bearer {token}"}
        
        for attempt in range(retry_count):
            try:
                with open(file_path, "rb") as file_obj:
                    files = {"file": (relative_path, file_obj)}
                    response = requests.post(
                        f"{server_url}/secure-upload",
                        files=files,
                        headers=headers,
                        timeout=30
                    )
                    if response.status_code == 200:
                        logging.info("✅ Successfully uploaded %s", relative_path)
                        success_count += 1
                        break
                    else:
                        logging.warning(
                            "Attempt %d failed for %s: %s",
                            attempt + 1, relative_path, response.text
                        )
            except Exception as e:
                logging.warning("Attempt %d failed for %s: %s", attempt + 1, relative_path, e)
            
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)
        else:
            logging.error("❌ Failed to upload %s after %d attempts", relative_path, retry_count)
            fail_count += 1

    logging.info(
        "Upload complete: %d succeeded, %d failed out of %d total", 
        success_count, fail_count, total
    )

    return {
        "success": success_count, 
        "failed": fail_count, 
        "total": total
    }

# ========== 主程序 ==========
if __name__ == "__main__": 
    current_dir = os.path.dirname(os.path.abspath(__file__))
    main_dir = os.path.realpath(os.path.join(current_dir, ".."))
    folder_path = os.path.join(main_dir, "buildin")
    config_path = os.path.join(current_dir, "config.json")

    if not os.path.exists(config_path): 
        logging.error("Config file not found: %s", config_path)
        logging.error("Please create config.json with: {\"upload_url\": \"http://...\", \"password\": \"...\"}")
        exit(1)

    with open(config_path, "r") as f: 
        config = json.load(f)

    if "upload_url" not in config or "password" not in config: 
        logging.error("Config must contain \"upload_url\" and \"password\"")
        exit(1)

    # 选择上传模式
    # MODE = "transactional"  # 全部成功或全部失败
    MODE = "transactional"  # 尽力上传，失败的不影响成功的
    
    if MODE == "transactional":
        result = upload_folder_transactional(
            folder_path, 
            config["upload_url"], 
            config["password"]
        )
    else: 
        result = {
            "success": 0, 
            "failed": 0, 
            "total": 0,
            "details": "No upload mode selected"
        }
    '''
    elif MODE == "force":
        result = upload_folder_force(
            folder_path, 
            config["upload_url"], 
            config["password"]
        )
    else:
        result = upload_folder_single_files(
            folder_path, 
            config["upload_url"], 
            config["password"]
        )
    '''

    # 输出结果
    print(f"\n{'='*50}")
    print("Upload Summary:")
    print(f"  Success: {result['success']}")
    print(f"  Failed:  {result['failed']}")
    print(f"  Total:   {result['total']}")
    if "details" in result:
        print(f"  Details: {json.dumps(result['details'], indent=2)}")
    print(f"{'='*50}")