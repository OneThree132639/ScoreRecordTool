import logging
import os
import platform
import sys

from pathlib import Path

from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import QApplication

from src.SRTGui import MainWindow

def get_config_dir(app_name: str) -> Path: 
	if platform.system() == "Windows": 
		return Path.home() / "AppData" / "Roaming" / app_name
	elif platform.system() == "Darwin": 
		return Path.home() / "Library" / "Application Support" / app_name
	else: 
		return Path.home() / ".config" / app_name
	
def get_project_base_dir(app_name: str, is_debug: bool) -> str: 
	if is_debug: 
		return os.path.dirname(os.path.abspath(__file__))
	else: 
		return str(get_config_dir(app_name))

def get_resource_path() -> str: 
	try: 
		return sys._MEIPASS # type: ignore
	except Exception: 
		return os.path.dirname(os.path.abspath(__file__))

def load_fonts(font_dir: str) -> None: 
	if not os.path.exists(font_dir): 
		logging.warning("Font directory does not exist: %s", font_dir)
		return
	font_extensions = [".ttf", ".otf"]
	for font_file in os.listdir(font_dir): 
		if any(font_file.lower().endswith(ext) for ext in font_extensions): 
			font_path = os.path.join(font_dir, font_file)
			font_id = QFontDatabase.addApplicationFont(font_path)
			if font_id == -1: 
				logging.warning("Failed to load font: %s", font_file)
			else: 
				families = QFontDatabase.applicationFontFamilies(font_id)
				logging.info("Loaded font: %s, families: %s", font_file, families)

if __name__ == "__main__": 
	project_name = "ScoreRecordTool"
	version = "0.0.1"
	author = "OneThree"
	is_debug = False # False when commited

	project_base_dir = get_project_base_dir(project_name, is_debug)  # project data directory
	source_dir = get_resource_path()                                 # builtin directory
	data_dir = os.path.join(project_base_dir, "data")
	resource_dir = os.path.join(project_base_dir, "resource")
	buildin_dir = os.path.join(source_dir, "buildin")
	log_dir = os.path.join(data_dir, "log")
	font_dir = os.path.join(buildin_dir, "fonts")

	os.makedirs(data_dir, exist_ok=True)
	os.makedirs(log_dir, exist_ok=True)

	logging.basicConfig(
		level=logging.INFO, # INFO when commited
		format="%(asctime)s [%(levelname)s] %(message)s", 
		handlers=[
			logging.FileHandler(os.path.join(log_dir, "app.log"), mode="w"), 
			logging.StreamHandler()
		]
	)

	app = QApplication(sys.argv)
	font = QFont()
	font.setFamily("nintendo_NTLG-DB_001")
	font.setPointSize(12)
	font.setBold(False)
	app.setFont(font)
	load_fonts(font_dir)
	window = MainWindow(
		project_base_dir = project_base_dir, 
		data_dir = data_dir, 
		buildin_dir = buildin_dir, 
		resource_dir = resource_dir
	)
	window.show()
	sys.exit(app.exec_())