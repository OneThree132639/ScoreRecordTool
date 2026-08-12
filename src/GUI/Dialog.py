from typing import Callable, Generator, List, Optional, Tuple, Union
from typing import overload

from PyQt5.QtCore import (
	pyqtSignal, QObject, QThread, QTimer
)
from PyQt5.QtWidgets import (
	QApplication, QDialog, QGridLayout, QLabel, QProgressBar, QWidget
)

def centerDialog(dialog: QDialog, parent: Optional[QWidget]=None) -> None: 
	dialog_size = dialog.size()

	if parent is not None and parent.isVisible(): 
		parent_rect = parent.geometry()
		center_x = parent_rect.x() + parent_rect.width() // 2
		center_y = parent_rect.y() + parent_rect.height() // 2
	else: 
		screen = QApplication.primaryScreen()
		assert screen is not None
		screen = screen.geometry()
		center_x = screen.width() // 2
		center_y = screen.height() // 2

	x = center_x - dialog_size.width() // 2
	y = center_y - dialog_size.height() // 2
	dialog.move(x, y)

class MessageObject: 

	def __init__(self, task_id: int, task_name: str, task_func: Callable[[], None]) -> None: 
		self.task_id = task_id
		self.task_name = task_name
		self.task_func = task_func

class ProgressObject: 

	def __init__(self, task_id: int, task_name: str, 
			task_func: Callable[[], Generator[Tuple[str, int, int], None, None]]
		) -> None: 
		self.task_id = task_id
		self.task_name = task_name
		self.task_func = task_func

class MessageDialog(QDialog): 

	def __init__(self, title: str, message: str, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.setWindowTitle(title)
		self.setModal(True)
		self.setFixedSize(400, 200)
		centerDialog(self, parent)

		self.main_layout = QGridLayout()
		self.label = QLabel(message)
		self.main_layout.addWidget(self.label, 0, 0)

		self.setLayout(self.main_layout)

	def updateStatus(self, message: str) -> None: 
		self.label.setText(message) 

class ProgressDialog(QDialog): 

	def __init__(self, 
			title: str, message: str, 
			parent: Optional[QWidget]=None
		): 
		super().__init__(parent)
		self.setWindowTitle(title)
		self.setModal(True)
		self.setFixedSize(400, 200)
		centerDialog(self, parent)

		self.main_layout = QGridLayout()
		self.label = QLabel(message)
		self.main_layout.addWidget(self.label, 0, 0)

		self.progress_bar = QProgressBar(self)
		self.progress_bar.setValue(0)
		self.main_layout.addWidget(self.progress_bar, 1, 0)

		self.setLayout(self.main_layout)

	def updateStatus(self, message: str, progress_value: int, progress_range: int) -> None: 
		self.label.setText(message)
		self.progress_bar.setValue(progress_value)
		self.progress_bar.setRange(0, progress_range)

class MessageWorker(QThread): 

	progress_updated = pyqtSignal(str)
	update_finished = pyqtSignal()

	def __init__(self, task_id: int, task_name: str, task_func: Callable[[], None]) -> None: 
		super().__init__()
		self.task_id = task_id
		self.task_name = task_name
		self.task_func = task_func

	def run(self) -> None: 
		self.progress_updated.emit(self.task_name)
		self.task_func()
		self.update_finished.emit()

class ProgressWorker(QThread): 

	progress_updated = pyqtSignal(str, int, int)
	update_finished = pyqtSignal()

	def __init__(self, task_id: int, task_name: str, task_func: Callable[[], Generator[Tuple[str, int, int], None, None]]) -> None: 
		super().__init__()
		self.task_id = task_id
		self.task_name = task_name
		self.task_func = task_func

	def run(self) -> None: 
		for msg, progress_value, progress_range in self.task_func(): 
			self.progress_updated.emit(msg, progress_value, progress_range)
		self.update_finished.emit()

class UpdateController(QObject): 

	all_updates_finished = pyqtSignal()

	def __init__(self, parent: Optional[QWidget]=None) -> None: 
		super().__init__(parent)
		self.my_parent = parent
		self.current_worker: Optional[Union[MessageWorker, ProgressWorker]] = None
		self.task_queue: List[Union[MessageObject, ProgressObject]] = []
		self.current_index = 0

	def appendTask(self, task_object: Union[MessageObject, ProgressObject]) -> "UpdateController": 
		self.task_queue.append(task_object)
		return self

	@overload
	def _generateDialog(self, task_object: MessageObject) -> MessageDialog: ...
	@overload
	def _generateDialog(self, task_object: ProgressObject) -> ProgressDialog: ...
	def _generateDialog(self, task_object: Union[MessageObject, ProgressObject]) -> Union[MessageDialog, ProgressDialog]: 
		dialog_title = "Updating progress ({}/{})".format(self.current_index + 1, len(self.task_queue))
		if isinstance(task_object, MessageObject): 
			return MessageDialog(dialog_title, task_object.task_name, self.my_parent)
		elif isinstance(task_object, ProgressObject): 
			return ProgressDialog(dialog_title, task_object.task_name, self.my_parent)

	@overload
	def _generateWorker(self, task_object: MessageObject, dialog: MessageDialog) -> MessageWorker: ... 
	@overload
	def _generateWorker(self, task_object: ProgressObject, dialog: ProgressDialog) -> ProgressWorker: ...
	def _generateWorker(self, 
			task_object: Union[MessageObject, ProgressObject], 
			dialog: Union[MessageDialog, ProgressDialog]
		) -> Union[MessageWorker, ProgressWorker]: 
		if isinstance(task_object, MessageObject) and isinstance(dialog, MessageDialog): 
			worker = MessageWorker(task_object.task_id, task_object.task_name, task_object.task_func)
			worker.progress_updated.connect(dialog.updateStatus)
		elif isinstance(task_object, ProgressObject) and isinstance(dialog, ProgressDialog): 
			worker = ProgressWorker(task_object.task_id, task_object.task_name, task_object.task_func)
			worker.progress_updated.connect(dialog.updateStatus)
		else: 
			raise TypeError("Invalid task object")
		worker.update_finished.connect(lambda: self._onTaskCompleted(dialog))
		return worker

	def start(self) -> None: 
		if not self.task_queue: 
			self.all_updates_finished.emit()
			return

		self.current_index = 0
		self._runNextTask()

	def _runNextTask(self) -> None: 
		if self.current_index >= len(self.task_queue): 
			self.all_updates_finished.emit()
			return

		dialog = self._generateDialog(self.task_queue[self.current_index])
		dialog.show()

		self.current_worker = self._generateWorker(self.task_queue[self.current_index], dialog)
		self.current_worker.start()

	def _onTaskCompleted(self, dialog: Union[MessageDialog, ProgressDialog]) -> None: 
		dialog.accept()
		self.current_index += 1
		QTimer.singleShot(300, self._runNextTask)