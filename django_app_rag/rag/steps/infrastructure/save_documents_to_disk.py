import shutil
from pathlib import Path
from typing_extensions import Annotated
from zenml import get_step_context, step

from django_app_rag.rag.models import Document


@step
def save_documents_to_disk(
    documents: list,
    output_dir: Path,
) -> Annotated[str, "output"]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Sauvegarder chaque document
    for doc in documents:
        doc.write(output_dir=output_dir, obfuscate=True, also_save_as_txt=True)

    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="output",
        metadata={
            "count": len(documents),
            "output_dir": str(output_dir),
        },
    )

    return str(output_dir)
