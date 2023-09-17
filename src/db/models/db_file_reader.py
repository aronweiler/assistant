from io import IOBase

from src.db.models.documents import Documents


class DBFileReader(IOBase):
    """A file-like object that reads from a file in the database"""
    document_helper: Documents = Documents()

    def __init__(self, file_id: int):
        self.file_id = file_id

    def read(self, size=-1):
        return self.document_helper.get_file(self.file_id).file_data

    def write(self, data):
        raise NotImplementedError("Can't use this class to write!")

    def seek(self, offset, whence=0):
        raise NotImplementedError("No Seekers!!")

    def tell(self):
        raise NotImplementedError("Don't even know what tell does...")

    def close(self):
        pass  # Optionally implement close() if needed
