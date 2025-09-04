import json
from pathlib import Path
import random
from pydantic import BaseModel, Field
from datasets import Dataset, DatasetDict
from django_app_rag.logging import get_logger_loguru

logger = get_logger_loguru(__name__)
from django_app_rag.rag import utils
from typing import Literal


class DocumentMetadata(BaseModel):
    id: str
    url: str
    title: str
    properties: dict
    source_type: Literal["notion", "url", "file"] = Field(description="Type de source du document")

    def obfuscate(self) -> "DocumentMetadata":
        """Create an obfuscated version of this metadata by modifying in place.

        Returns:
            DocumentMetadata: Self, with ID and URL obfuscated.
        """

        original_id = self.id.replace("-", "")
        fake_id = utils.generate_random_hex(len(original_id))

        self.id = fake_id
        self.url = self.url.replace(original_id, fake_id)

        return self


class Document(BaseModel):
    id: str
    metadata: DocumentMetadata
    parent_metadata: DocumentMetadata | None = None
    content: str
    content_quality_score: float | None = None
    summary: str | None = None
    child_urls: list[str] = Field(default_factory=list)

    def __init__(self, **data):
        # Si l'ID n'est pas fourni, générer automatiquement un hash du contenu
        if 'id' not in data and 'content' in data:
            data['id'] = utils.generate_content_hash(data['content'])
        
        super().__init__(**data)
        
        # Mettre à jour l'ID dans les métadonnées pour qu'il corresponde à l'ID du document
        if hasattr(self, 'metadata') and self.metadata and self.metadata.id != self.id:
            self.metadata.id = self.id

    @classmethod
    def from_file(cls, file_path: Path) -> "Document":
        """Read a Document object from a JSON file.

        Args:
            file_path: Path to the JSON file containing document data.

        Returns:
            Document: A new Document instance constructed from the file data.

        Raises:
            FileNotFoundError: If the specified file doesn't exist.
            ValidationError: If the JSON data doesn't match the expected model structure.
        """

        json_data = file_path.read_text(encoding="utf-8")

        return cls.model_validate_json(json_data)

    def add_summary(self, summary: str) -> "Document":
        self.summary = summary

        return self

    def add_quality_score(self, score: float) -> "Document":
        self.content_quality_score = score

        return self

    def write(
        self, output_dir: Path, obfuscate: bool = False, also_save_as_txt: bool = False
    ) -> None:
        """Write document data to file, optionally obfuscating sensitive information.

        Args:
            output_dir: Directory path where the files should be written.
            obfuscate: If True, sensitive information will be obfuscated.
            also_save_as_txt: If True, content will also be saved as a text file.
        """

        output_dir.mkdir(parents=True, exist_ok=True)

        if obfuscate:
            self.obfuscate()

        json_page = self.model_dump()

        output_file = output_dir / f"{self.id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                json_page,
                f,
                indent=4,
                ensure_ascii=False,
            )
            logger.info(f"Wrote metadata fordocument {self.id} to {output_file}")

        if also_save_as_txt:
            txt_path = output_file.with_suffix(".txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(self.content)
                logger.info(f"Wrote content for document {self.id} to {txt_path}")

    def obfuscate(self) -> "Document":
        """Create an obfuscated version of this document by modifying in place.

        Returns:
            Document: Self, with obfuscated metadata and parent_metadata.
        """

        self.metadata = self.metadata.obfuscate()
        self.parent_metadata = (
            self.parent_metadata.obfuscate() if self.parent_metadata else None
        )
        self.id = self.metadata.id

        return self

    def __eq__(self, other: object) -> bool:
        """Compare two Document objects for equality.

        Args:
            other: Another object to compare with this Document.

        Returns:
            bool: True if the other object is a Document with the same ID.
        """
        if not isinstance(other, Document):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Generate a hash value for the Document.

        Returns:
            int: Hash value based on the document's ID.
        """
        return hash(self.id)
    
class Collection(BaseModel):
    name: str
    documents: list[Document]


class InstructDatasetSample(BaseModel):
    instruction: str
    answer: str


class InstructDataset(BaseModel):
    train: list[InstructDatasetSample]
    validation: list[InstructDatasetSample]
    test: list[InstructDatasetSample]
    val_split_ratio: float
    test_split_ratio: float
    seed: int | None = None

    @classmethod
    def from_samples(
        cls,
        samples: list[InstructDatasetSample],
        val_split_ratio: float,
        test_split_ratio: float,
        seed: int | None = None,
    ) -> "InstructDataset":
        """Creates an InstructDataset by splitting samples into train/val/test sets.

        Args:
            samples: List of samples to split
            val_split_ratio: Ratio of samples to use for validation (between 0 and 1)
            test_split_ratio: Ratio of samples to use for testing (between 0 and 1)
            seed: Random seed for shuffling. If None, no fixed seed is used.

        Returns:
            InstructDataset with shuffled and split samples
        """

        shuffled_samples = samples.copy()

        if seed is not None:
            random.seed(seed)
        random.shuffle(shuffled_samples)

        train_samples = shuffled_samples[
            : int(len(shuffled_samples) * (1 - val_split_ratio - test_split_ratio))
        ]
        val_samples = shuffled_samples[
            int(len(shuffled_samples) * (1 - val_split_ratio - test_split_ratio)) : int(
                len(shuffled_samples) * (1 - test_split_ratio)
            )
        ]
        test_samples = shuffled_samples[
            int(len(shuffled_samples) * (1 - test_split_ratio)) :
        ]

        logger.info(
            "Created dataset with the following splits: "
            f"- Train samples: {len(train_samples)}, "
            f"- Validation samples: {len(val_samples)}, "
            f"Test samples: {len(test_samples)}"
        )

        assert len(train_samples) > 0, "Train split must have at least one sample"
        assert len(val_samples) > 0, "Validation split must have at least one sample"
        assert len(test_samples) > 0, "Test split must have at least one sample"

        return InstructDataset(
            train=train_samples,
            validation=val_samples,
            test=test_samples,
            val_split_ratio=val_split_ratio,
            test_split_ratio=test_split_ratio,
            seed=seed,
        )

    def to_huggingface(self) -> DatasetDict:
        train = Dataset.from_list([sample.model_dump() for sample in self.train])
        validation = Dataset.from_list(
            [sample.model_dump() for sample in self.validation]
        )
        test = Dataset.from_list([sample.model_dump() for sample in self.test])

        return DatasetDict({"train": train, "validation": validation, "test": test})

    def write(self, output_dir: Path) -> Path:
        """Writes the dataset splits to JSON files in the specified directory.

        Args:
            output_dir: Directory path where the dataset files will be saved

        Returns:
            Path to the output directory containing the saved files
        """
        train = [sample.model_dump() for sample in self.train]
        validation = [sample.model_dump() for sample in self.validation]
        test = [sample.model_dump() for sample in self.test]

        output_dir.mkdir(parents=True, exist_ok=True)

        for split_name, samples in {
            "train": train,
            "validation": validation,
            "test": test,
        }.items():
            output_file = output_dir / f"{split_name}.json"
            with open(output_file, "w") as f:
                json.dump(samples, f, indent=2)

        logger.info(f"Wrote dataset splits to {output_dir}")

        return output_dir