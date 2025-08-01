from pathlib import Path

from loguru import logger
from typing_extensions import Annotated
from zenml.steps import get_step_context, step

from django_app_rag.rag.models import Document


@step
def read_documents_from_disk(
    data_directory: Path, nesting_level: int = 0
) -> Annotated[list[Document], "documents"]:
    pages: list[Document] = []

    logger.info(f"Reading documents from '{data_directory}'")

    if not data_directory.exists():
        raise FileNotFoundError(f"Directory not found: '{data_directory}'")

    json_files = __get_json_files(
        data_directory=data_directory, nesting_level=nesting_level
    )
    for json_file in json_files:
        page = Document.from_file(json_file)
        pages.append(page)

    logger.info(f"Successfully read {len(pages)} documents from disk.")

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="documents",
        metadata={
            "count": len(pages),
        },
    )

    return pages


def __get_json_files(data_directory: Path, nesting_level: int = 0) -> list[Path]:
    if nesting_level == 0:
        return list(data_directory.glob("*.json"))
    else:
        json_files = []
        for database_dir in data_directory.iterdir():
            if database_dir.is_dir():
                nested_json_files = __get_json_files(
                    data_directory=database_dir, nesting_level=nesting_level - 1
                )
                json_files.extend(nested_json_files)

        return json_files
