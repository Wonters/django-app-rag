import msgpack
from pathlib import Path
from pydantic import BaseModel
from typing import Union, Type, List
from uuid import uuid4
from loguru import logger


class DiskStorage:
    """
    Storage class for saving and loading data to disk using msgpack serialization.
    """
    storage_path: Path= Path("data") / "storage"
    model_class: Type[BaseModel]
    collection_name: str
    
    def __init__(self,model_class: Type[BaseModel], collection_name: str):
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.model_class = model_class
        self.collection_name = collection_name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    @property
    def location(self) -> Path:
        return self.storage_path / f"{self.collection_name}.msgpack"

    def save(self, data: List[BaseModel]):
        if not isinstance(data[0], self.model_class):
            logger.error(f"Data {type(data[0])} is not an instance of {self.model_class}")
            # raise ValueError(f"Data {type(data[0])} is not an instance of {self.model_class}")
        data = [item.model_dump() for item in data]
        with open(self.location, "wb") as f:
            f.write(msgpack.packb(data))
            logger.info(f"Saved {self.collection_name} to {self.storage_path}")

    def read(self) -> List[BaseModel]:
        """
        Read the data from the disk storage.
        """
        with open(self.location, "rb") as f:
            data = msgpack.unpackb(f.read())
            return [self.model_class.model_validate(item) for item in data]

    def clear_collection(self):
        if self.location.exists():
            self.location.unlink()
