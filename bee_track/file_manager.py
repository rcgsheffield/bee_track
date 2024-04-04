import threading
import os
import datetime
import glob
import zipfile


class FileManager:
    def __init__(self, message_queue):
        self.message_queue = message_queue

    def compress_photos(self):
        """
        Add photos to a ZIP archive
        """

        # List photo files
        files = glob.glob('*.np')

        # Create ZIP archive
        zipfilename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip"
        with zipfile.ZipFile(zipfilename, "w", ZIP_DEFLATED) as zip_archive:
            # Iterate over photos
            for i, file in enumerate(files):
                self.message_queue.put("Compressing files (%d of %d)" % (i, len(files)))
                self.message_queue.put("<a href='%s'>download</a>" % zipfilename)
                print("Compressing %s" % file)
                zip_archive.write(file)
