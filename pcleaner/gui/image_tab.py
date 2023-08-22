from pathlib import Path
from typing import Callable

import PySide6.QtCore as Qc
import PySide6.QtWidgets as Qw
from PySide6.QtCore import Slot
from logzero import logger

import pcleaner.config as cfg
import pcleaner.gui.image_details_driver as idd
import pcleaner.gui.image_file as imf
import pcleaner.gui.structures as st


# noinspection PyPep8Naming
class ImageTab(Qw.QTabWidget):
    """
    Manage the static tab for the file table and the dynamic tabs showing the image
    previews/outputs.
    """

    # Currently open dynamic tabs: path -> (image structure, tab's widget)
    open_images: dict[Path, tuple[imf.ImageFile, Qw.QWidget]]

    def __init__(self, parent=None):
        Qw.QTabWidget.__init__(self, parent)
        self.setAcceptDrops(True)

        self.open_images = {}

        self.tabCloseRequested.connect(self.tab_close)

    @Slot(imf.ImageFile)
    def open_image(
        self,
        image_obj: imf.ImageFile,
        config: cfg.Config,
        shared_ocr_model: st.Shared[st.OCRModel],
        thread_queue: Qc.QThreadPool,
        progress_callback: Callable[[imf.ProgressData], None],
    ):
        """
        Check if the image is already open, in which case show it.
        Otherwise create a new tab.

        :param image_obj: Image object to open.
        :param config: The config object.
        :param shared_ocr_model: The shared OCR model.
        :param thread_queue: The thread queue for processing steps.
        :param progress_callback: The callback to call when a step is done.
        """
        if image_obj.path in self.open_images:
            self.setCurrentWidget(self.open_images[image_obj.path][1])
            return

        # Create the tab.
        tab = idd.ImageDetailsWidget(
            image_obj=image_obj,
            config=config,
            shared_ocr_model=shared_ocr_model,
            thread_queue=thread_queue,
            progress_callback=progress_callback,
        )
        self.addTab(tab, image_obj.path.name)
        self.open_images[image_obj.path] = (image_obj, tab)
        self.setCurrentWidget(tab)

    @Slot(int)
    def tab_close(self, index: int):
        """
        Close the image details tab.

        :param index: The index of the tab to close.
        """
        # Make sure the index is not the primary tab.
        if index == 0:
            logger.warning("Attempted to close the primary tab.")
            return
        logger.debug(f"Closing tab at index {index}.")
        # The tab we're closing must be an image details tab.
        # noinspection PyTypeChecker
        widget_to_close: idd.ImageDetailsWidget = self.widget(index)
        path = widget_to_close.image_obj.path
        self.open_images.pop(path)
        self.removeTab(index)