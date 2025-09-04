from pathlib import Path
from typing_extensions import Annotated
from zenml import get_step_context, step
from django_app_rag.logging import get_logger_loguru
from django_app_rag.rag.models import Document

logger = get_logger_loguru(__name__)

@step
def save_documents_to_disk(
    documents: list,
    output_dir: Path,
    storage_mode: str = "overwrite",
) -> Annotated[str, "output"]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if storage_mode == "overwrite":
        for file in output_dir.glob("*"):
            file.unlink()

    # Sauvegarder chaque document
    for doc in documents:
        logger.info(f"Saving document {doc.id} to {output_dir}")
        doc.write(output_dir=output_dir, obfuscate=False, also_save_as_txt=True)

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="output",
        metadata={
            "count": len(documents),
            "output_dir": str(output_dir),
        },
    )

    return str(output_dir)
