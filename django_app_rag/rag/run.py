import click
from smolagents import GradioUI
from django_app_rag.rag.pipelines.compute_rag_vector_index import (
    compute_rag_vector_index,
)
from django_app_rag.rag.pipelines.collect_data import collect_data
from django_app_rag.rag.pipelines.etl import etl_mixed
from django_app_rag.rag.pipelines.generate_dataset import generate_dataset
from pathlib import Path
from django_app_rag.rag.agents.tools import get_agent
import yaml


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Chemin du fichier de configuration YAML",
)
def retrieve(config):
    """Récupérer les données depuis les fichiers, URLs et Notion"""
    with open(config, "r") as f:
        cfg = yaml.safe_load(f)

    # Conversion des chemins de fichiers en objets Path
    file_paths = None
    if cfg.get("file_paths"):
        file_paths = [Path(p) for p in cfg["file_paths"]]

    collect_data(
        data_dir=Path(cfg["data_dir"]),
        file_paths=file_paths,
        urls=cfg.get("urls"),
        notion_database_ids=cfg.get("notion_database_ids"),
        to_s3=cfg.get("to_s3", False),
        max_workers=cfg.get("max_workers", 10),
    )


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Chemin du fichier de configuration YAML",
)
def etl(config):
    with open(config, "r") as f:
        cfg = yaml.safe_load(f)
    etl_mixed(
        data_dir=Path(cfg["data_dir"]),
        collection_name=cfg["collection_name"],
        to_s3=cfg["to_s3"],
        max_workers=cfg["max_workers"],
        quality_agent_model_id=cfg["quality_agent_model_id"],
        quality_agent_mock=cfg["quality_agent_mock"],
        include_notion=cfg.get("include_notion", True),
        include_files=cfg.get("include_files", True),
        include_urls=cfg.get("include_urls", True),
    )


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Chemin du fichier de configuration YAML",
)
def create_dataset(config):
    with open(config, "r") as f:
        cfg = yaml.safe_load(f)
    generate_dataset(
        collection_name=cfg["collection_name"],
        load_dataset_id=cfg["load_dataset_id"],
        fetch_limit=cfg["fetch_limit"],
        summarization_agent_model_id=cfg["summarization_agent_model_id"],
        summarization_agent_mock=cfg["summarization_agent_mock"],
        summarization_max_characters=cfg["summarization_max_characters"],
        val_split_ratio=cfg["val_split_ratio"],
        test_split_ratio=cfg["test_split_ratio"],
        min_document_characters=cfg["min_document_characters"],
    )


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Chemin du fichier de configuration YAML",
)
def index(config):
    with open(config, "r") as f:
        cfg = yaml.safe_load(f)
    compute_rag_vector_index(
        collection_name=cfg["collection_name"],
        fetch_limit=cfg["fetch_limit"],
        content_quality_score_threshold=cfg["content_quality_score_threshold"],
        retriever_type=cfg["retriever_type"],
        embedding_model_id=cfg["embedding_model_id"],
        embedding_model_type=cfg["embedding_model_type"],
        embedding_model_dim=cfg["embedding_model_dim"],
        chunk_size=cfg["chunk_size"],
        vectorstore=cfg.get("vectorstore", "faiss"),
        contextual_summarization_type=cfg.get("contextual_summarization_type"),
        contextual_agent_model_id=cfg.get("contextual_agent_model_id"),
        contextual_agent_max_characters=cfg.get("contextual_agent_max_characters"),
        mock=cfg.get("mock"),
        data_dir=cfg.get("data_dir", "data"),
        device=cfg.get("device"),
    )


@cli.command()
@click.option(
    "--config",
    type=click.Path(exists=True),
    required=True,
    help="Chemin du fichier de configuration YAML",
)
@click.option(
    "--ui",
    is_flag=True,
    default=False,
    help="Launch with Gradio UI instead of CLI mode",
)
@click.option(
    "--query",
    "-q",
    type=str,
    default="What is the feature/training/inference (FTI) pipelines architecture?",
    help="Query to run in CLI mode",
)
def chat(config, ui, query):
    with open(config, "r") as f:
        retriever_config_path = yaml.safe_load(f)["retriever_config_path"]
    agent = get_agent(Path(retriever_config_path))
    if ui:
        GradioUI(agent).launch()
    else:
        assert query, "Query is required in CLI mode"
        result = agent.run(query)
        print(result)


if __name__ == "__main__":
    cli()
