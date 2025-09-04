from pathlib import Path
from typing_extensions import Annotated
from zenml import get_step_context, step
from django_app_rag.logging import get_logger_loguru

logger = get_logger_loguru(__name__)

@step
def move_tmp_files(
    data_dir: Path,
    storage_mode: str = "overwrite",
) -> Annotated[str, "output"]:
    """Move files from tmp directory to main directory when in append mode.
    
    Args:
        data_dir: Root data directory
        storage_mode: Storage mode - "overwrite" or "append"
        
    Returns:
        str: Path to the main data directory
    """
    if storage_mode != "append":
        logger.info("Storage mode is not 'append', no files to move")
        return str(data_dir)
    
    tmp_dir = data_dir / "tmp"
    if not tmp_dir.exists():
        logger.info(f"Tmp directory {tmp_dir} does not exist, nothing to move")
        return str(data_dir)
    
    logger.info(f"Moving files from {tmp_dir} to {data_dir}")
    
    # Move files from tmp to main directory
    for directory in tmp_dir.iterdir():
        if not directory.is_dir():
            continue
            
        target_dir = data_dir / directory.name
        logger.info(f"Processing directory: {directory.name}")
        
        if target_dir.exists():
            # If the target directory exists, merge the content
            logger.info(f"Merging content from {directory} to {target_dir}")
            for item in directory.iterdir():
                if item.is_file():
                    # For files, move them directly
                    target_file = target_dir / item.name
                    if target_file.exists():
                        logger.info(f"File {item.name} already exists, skipping")
                        continue
                    item.rename(target_file)
                    logger.info(f"Moved file: {item.name}")
                elif item.is_dir():
                    # For subdirectories, merge recursively
                    target_subdir = target_dir / item.name
                    if target_subdir.exists():
                        # If the subdirectory exists, merge its content
                        logger.info(f"Merging subdirectory: {item.name}")
                        for subitem in item.iterdir():
                            target_subitem = target_subdir / subitem.name
                            if target_subitem.exists():
                                logger.info(f"Subitem {subitem.name} already exists, skipping")
                                continue
                            subitem.rename(target_subitem)
                            logger.info(f"Moved subitem: {subitem.name}")
                        item.rmdir()  # Remove empty directory
                    else:
                        # If the subdirectory doesn't exist, move it
                        item.rename(target_subdir)
                        logger.info(f"Moved subdirectory: {item.name}")
            directory.rmdir()  # Remove empty directory
        else:
            # If the target directory doesn't exist, move it normally
            directory.rename(target_dir)
            logger.info(f"Moved directory: {directory.name}")
    
    # Remove tmp directory if it's empty
    try:
        tmp_dir.rmdir()
        logger.info(f"Removed empty tmp directory: {tmp_dir}")
    except OSError:
        logger.info(f"Tmp directory {tmp_dir} is not empty, keeping it")
    
    step_context = get_step_context()
    step_context.add_output_metadata(
        output_name="output",
        metadata={
            "source_dir": str(tmp_dir),
            "target_dir": str(data_dir),
            "storage_mode": storage_mode,
        },
    )
    
    logger.info("File moving completed successfully")
    return str(data_dir)
