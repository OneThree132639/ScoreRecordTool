import logging
import json
import os
import requests
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(
	level=logging.INFO, 
	format="%(asctime)s - %(levelname)s - %(message)s", 
	handlers=[logging.StreamHandler()]
)

def login_and_get_token(server_url: str, password: str) -> Optional[str]: 
	try: 
		response = requests.post(
			"{}/login".format(server_url), 
			params={"password": password}, 
			timeout=10
		)

		if response.status_code != 200: 
			logging.error("Login failed: %s", response.text)
			return None

		token = response.json().get("access_token")
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
	folderpath = Path(folder_path)
	if not folderpath.exists(): 
		logging.error("Folder does not exist: %s", folderpath)
		return {"success": 0, "failed": 0, "total": 0}

	token = login_and_get_token(server_url, password)
	if not token: 
		logging.error("Failed to get access token")
		return {"success": 0, "failed": 0, "total": 0}

	headers = {"Authorization": f"Bearer {token}"}

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

		for _, (_, file_obj) in files_data:
			file_obj.close()

		return {
			"success": 0,
			"failed": total,
			"total": total,
			"error": str(e)
		}

def upload_file_secure(
	file_path: str, relative_path: str, server_url: str, 
	token: str, retry_count: int=3
) -> bool: 
	headers = {"Authorization": "Bearer {}".format(token)}

	for attempt in range(retry_count): 
		try: 
			with open(file_path, "rb") as file_obj: 
				files = {"file": (relative_path, file_obj)}
				response = requests.post(
					"{}/secure-upload".format(server_url), 
					files=files, 
					headers=headers, 
					timeout=30
				)
				if response.status_code == 200: 
					logging.info("Successfully uploaded %s", relative_path)
					return True
				else: 
					logging.warning(
						"Upload attempt %d failed for %s: %s", 
						attempt + 1, 
						relative_path, 
						response.text
					)

					if response.status_code in (401, 403): 
						logging.error("Authentication failed, stopping retries. ")
						return False
		except requests.exceptions.RequestException as e: 
			logging.warning(
				"Upload attempt %d failed for %s: %s", 
				attempt + 1, 
				relative_path, 
				e
			)

		if attempt < retry_count - 1: 
			time.sleep(2**attempt)

	logging.error("Failed to upload: %s", relative_path)
	return False
	

def upload_folder(
	folder_path: str, server_url: str, password: str, max_files: Optional[int]=None
) -> dict: 
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

	logging.info("Starting upload of %d files...", len(files_to_upload))

	for idx, (file_path, relative_path) in enumerate(files_to_upload, 1): 
		logging.info("[%d/%d] Uploading: %s", idx, len(files_to_upload), relative_path)

		if upload_file_secure(file_path, relative_path, server_url, token): 
			success_count += 1
		else: 
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



if __name__ == "__main__": 
	current_dir = os.path.dirname(os.path.abspath(__file__))
	main_dir = os.path.realpath(os.path.join(current_dir, ".."))
	folder_path = os.path.join(main_dir, "buildin")
	config_path = os.path.join(current_dir, "config.json")

	if not os.path.exists(config_path): 
		logging.error("Config file not found: %s", config_path)
		logging.error("Please create a config.json with: {\"upload_url\": \"http://...\", \"password\": \"...\"}")
		exit(1)

	with open(config_path, "r") as f: 
		config = json.load(f)

	if "upload_url" not in config or "password" not in config: 
		logging.error("Config must contain \"upload_url\" and \"password\"")
		exit(1)

	result = upload_folder_transactional(folder_path, config["upload_url"], config["password"])

	logging.info((
		"\n{}\n"
		"Upload Summary: \n"
		"    Success: {}\n"
		"    Failed: {}\n"
		"    Total: {}\n"
		"{}"
	).format("="*50, result["success"], result["failed"], result["total"], "="*50))