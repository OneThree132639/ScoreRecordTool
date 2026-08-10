import jwt
import magic
import logging
import os
import re
import secrets
import shutil
import uuid

from datetime import datetime, timedelta, timezone
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
from typing import Dict, List, Optional

app = FastAPI()

# ========== Config ==========
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
UPLOAD_PASSWORD = os.getenv("UPLOAD_PASSWORD", "")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024 # 2 GB
ENABLE_VERSIONING = os.getenv("ENABLE_VERSIONING", "true").lower() == "true"
MAX_VERSIONS = int(os.getenv("MAX_VERSIONS", "5"))

ALLOWED_EXTENSIONS = {
	".pdf", ".jpg", ".jpeg", ".png", ".gif", ".txt", ".json", ".csv", 
	".npz", ".npy", ".otf", ".ttf", ".icns", ".ico"
}
ALLOWED_FILENAMES = {"manifest"}

security = HTTPBearer()

# ========== Directory Setup ==========
DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(DIR, "uploads")
TEMP_DIR = os.path.join(DIR, "temp_uploads")
VERSIONS_DIR = os.path.join(DIR, "versions")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(VERSIONS_DIR, exist_ok=True)

# ========== Token Authorization ==========
def create_access_token(data: dict, expires_delta: Optional[timedelta]=None) -> str: 
	to_encode = data.copy()
	utc_now = datetime.now(timezone.utc)
	if expires_delta: 
		expire = utc_now + expires_delta
	else: 
		expire = utc_now + timedelta(minutes=15)
	to_encode.update({"exp": expire})
	encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
	return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict: 
	token = credentials.credentials
	logging.info("Received token: {}".format(token[:10]))
	logging.info("Token length: {}".format(len(token)))
	try: 
		payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
		return payload
	except jwt.ExpiredSignatureError: 
		logging.error("Token expired")
		raise HTTPException(status_code=401, detail="Token has expired")
	except jwt.InvalidTokenError as e: 
		logging.error("Invalid token error: {}".format(str(e)))
		logging.error("Token: {}".format(token))
		raise HTTPException(status_code=401, detail="Invalid token")

# ========== Security Utilities ==========
def sanitize_filename(filename: str) -> str: 
	if not filename: 
		raise HTTPException(status_code=400, detail="Filename cannot be empty")

	filename = os.path.basename(filename)
	filename = re.sub("[^\\w\\-_.]", "", filename)

	if not filename: 
		raise HTTPException(status_code=400, detail="Invalid filename")

	root, ext = os.path.splitext(filename)
	root = root.lower()
	ext = ext.lower()
	if ext not in ALLOWED_EXTENSIONS and root not in ALLOWED_FILENAMES: 
		raise HTTPException(
			status_code=400, 
			detail="File type {} not allowed. Allowed: {}".format(ext, ALLOWED_EXTENSIONS)
		)

	return filename

def generate_unique_filename(original_filename: str) -> str: 
	name, ext = os.path.splitext(original_filename)
	time_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
	ramdom_suffix = secrets.token_hex(4)
	return "{}_{}_{}{}".format(name, time_stamp, ramdom_suffix, ext)

def get_version_path(filename: str, version: int) -> str: 
	name, ext = os.path.splitext(filename)
	version_dir = os.path.join(VERSIONS_DIR, name)
	os.makedirs(version_dir, exist_ok=True)
	return os.path.join(version_dir, "v{}{}".format(str(version).zfill(3), ext))

def get_current_version(filename: str) -> int: 
	name, _ = os.path.splitext(filename)
	version_dir = os.path.join(VERSIONS_DIR, name)
	if not os.path.exists(version_dir): 
		return 0
	versions = []
	for f in os.listdir(version_dir): 
		match = re.search("v(\\d+)", f)
		if match: 
			versions.append(int(match.group[1])) # type: ignore
	return max(versions) if versions else 0

def save_with_versioning(filename: str, content: bytes) -> dict: 
	name, ext = os.path.splitext(filename)
	current_version = get_current_version(filename)

	if os.path.exists(os.path.join(UPLOAD_DIR, filename)): 
		new_version = current_version + 1

		if ENABLE_VERSIONING: 
			version_path = get_version_path(filename, new_version)
			with open(version_path, "wb") as f: 
				f.write(content)

			versions_dir = os.path.join(VERSIONS_DIR, name)
			version_files = sorted([
				f for f in os.listdir(versions_dir)
				if f.startswith("v") and f.endswith(ext)
			])

			if len(version_files) > MAX_VERSIONS: 
				for old_file in version_files[:MAX_VERSIONS]: 
					os.remove(os.path.join(versions_dir, old_file))

			target_path = os.path.join(UPLOAD_DIR, filename)
			with open(target_path, "wb") as f: 
				f.write(content)

			return {
				"path": target_path, 
				"version": new_version, 
				"is_new": False, 
				"message": "Updated to version {}".format(new_version)
			}
		else: 
			target_path = os.path.join(UPLOAD_DIR, filename)
			with open(target_path, "wb") as f: 
				f.write(content)
			return {
				"path": target_path, 
				"version": current_version + 1, 
				"is_new": False, 
				"message": "File overwritten"
			}
	else: 
		target_path = os.path.join(UPLOAD_DIR, filename)
		with open(target_path, "wb") as f: 
			f.write(content)

		if ENABLE_VERSIONING: 
			version_path = get_version_path(filename, 1)
			with open(version_path, "wb") as f: 
				f.write(content)

		return {
			"path": target_path, 
			"version": 1, 
			"is_new": True, 
			"message": "New file created"
		}


async def validate_file_content(file: UploadFile) -> bytes: 
	content = await file.read()

	if len(content) > MAX_FILE_SIZE: 
		raise HTTPException(
			status_code=413, 
			detail="File too large. Max size: {} MB".format(MAX_FILE_SIZE // 1024 // 1024)
		)

	try: 
		mime_type = magic.from_buffer(content[:1024], mime=True)
	except: 
		pass

	return content

# ========== API Endpoints ==========
@app.post("/login")
async def login(password: str) -> Dict[str, str]: 
	if not UPLOAD_PASSWORD: 
		raise HTTPException(
			status_code=500, 
			detail="Server not configured properly"
		)
	
	if password != UPLOAD_PASSWORD: 
		raise HTTPException(status_code=401, detail="Incorrect password")

	access_token = create_access_token(
		data={"sub": "upload_user"}, 
		expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
	)
	return {"access_token": access_token, "token_type": "bearer"}

@app.post("/secure-upload")
async def secure_upload_file(
	file: UploadFile = File(...), 
	token_data: dict = Depends(verify_token)
): 
	original_filename = file.filename or "unnamed"
	safe_filename = sanitize_filename(original_filename)
	content = await validate_file_content(file)

	result = save_with_versioning(safe_filename, content)

	return {
		"message": "File uploaded successfully. ", 
		"original_name": original_filename, 
		"stored_name": safe_filename, 
		"size": len(content), 
		"version": result["version"], 
		"is_new": result["is_new"], 
		"detail": result["message"]
	}

@app.post("/secure-upload-folder")
async def secure_upload_folder(
	files: List[UploadFile] = File(...), 
	token_data: dict = Depends(verify_token)
): 
	temp_session_dir = os.path.join(TEMP_DIR, secrets.token_hex(16))
	os.makedirs(temp_session_dir, exist_ok=True)

	uploaded_files = []
	failed_files = []
	total_size = 0

	try: 
		for file in files: 
			try: 
				original_filename = file.filename or "unnamed"
				safe_filename = sanitize_filename(original_filename)
				content = await validate_file_content(file)

				total_size += len(content)
				if total_size > MAX_TOTAL_SIZE: 
					raise HTTPException(
						status_code=413, 
						detail="Total upload size exceed limit: {} GB".format(MAX_TOTAL_SIZE // 1024 // 1024 // 1024)
					)

				temp_path = os.path.join(temp_session_dir, safe_filename)
				with open(temp_path, "wb") as f: 
					f.write(content)

				uploaded_files.append({
					"original": original_filename, 
					"stored": safe_filename, 
					"size": len(content), 
					"temp_path": temp_path
				})
			except Exception as e: 
				failed_files.append({
					"filename": file.filename, 
					"error": str(e)
				})
				raise HTTPException(
					status_code=400, 
					detail="File validation failed: {} - {}".format(file.filename, str(e))
				)

		final_results = []
		for file_info in uploaded_files: 
			try: 
				result = save_with_versioning(
					file_info["stored"], 
					open(file_info["temp_path"], "rb").read()
				)
				final_results.append({
					"original": file_info["original"], 
					"stored": file_info["stored"], 
					"size": file_info["size"], 
					"version": result["version"], 
					"is_new": result["is_new"], 
					"detail": result["message"]
				})
			except Exception as e: 
				raise HTTPException(
					status_code=500, 
					detail="Failed to move files to final directory: {}".format(str(e))
				)

		return {
			"message": "All {} files uploaded successfully.".format(len(final_results)), 
			"uploaded": final_results, 
			"total_size": total_size
		}

	except HTTPException: 
		raise
	except Exception as e: 
		raise HTTPException(
			status_code=500, 
			detail="Upload failed: {}".format(str(e))
		)
	finally: 
		if os.path.exists(temp_session_dir): 
			shutil.rmtree(temp_session_dir, ignore_errors=True) 

@app.get("/download/{filename}")
async def download_file(filename: str): 
	filename = os.path.basename(filename)
	if not filename: 
		raise HTTPException(status_code=400, detail="Invalid filename")
	
	filepath = os.path.join(UPLOAD_DIR, filename)
	if not os.path.exists(filepath): 
		raise HTTPException(status_code=404, detail="File \"{}\" not found. ".format(filename))
	return FileResponse(path=filepath, filename=filename)

@app.get("/download-version/{filename}/{version}")
async def download_version(
    filename: str,
    version: int,
    token_data: dict = Depends(verify_token)
):
    filename = os.path.basename(filename)
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    version_path = get_version_path(filename, version)
    if not os.path.exists(version_path):
        raise HTTPException(
            status_code=404,
            detail=f"Version {version} of '{filename}' not found"
        )
    
    return FileResponse(path=version_path, filename=f"{filename}_v{version}")


@app.get("/list-files")
async def list_files(token_data: dict = Depends(verify_token)): 
	files = []
	for f in os.listdir(UPLOAD_DIR): 
		filepath = os.path.join(UPLOAD_DIR, f)
		if os.path.isfile(filepath): 
			files.append({
				"name": f, 
				"size": os.path.getsize(filepath), 
				"modifed": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
			})
	return {"files": files}

@app.get("/file-versions/{filename}")
async def get_file_versions(
    filename: str,
    token_data: dict = Depends(verify_token)
):
    filename = os.path.basename(filename)
    if not filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    name, ext = os.path.splitext(filename)
    version_dir = os.path.join(VERSIONS_DIR, name)
    
    if not os.path.exists(version_dir):
        return {"filename": filename, "versions": []}
    
    versions = []
    for f in os.listdir(version_dir):
        match = re.search(r'v(\d+)(\..*)?$', f)
        if match:
            version_num = int(match.group(1))
            filepath = os.path.join(version_dir, f)
            versions.append({
                "version": version_num,
                "size": os.path.getsize(filepath),
                "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
            })
    
    return {
        "filename": filename,
        "current_version": get_current_version(filename),
        "versions": sorted(versions, key=lambda x: x["version"])
    }