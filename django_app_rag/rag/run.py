import click 
from smolagents import GradioUI
from django_app_rag.rag.pipelines.compute_rag_vector_index import compute_rag_vector_index
from django_app_rag.rag.pipelines.collect_notion_data import collect_notion_data
from django_app_rag.rag.pipelines.etl import etl as rag_etl
from django_app_rag.rag.pipelines.generate_dataset import generate_dataset
from pathlib import Path
from django_app_rag.rag.agents.tools import get_agent
@click.group()
def cli():
    pass

@cli.command()
def retrieve():
    collect_notion_data(
    database_ids=["2395d032ef3980d2a1e1c5c47a2f2d85"],
    data_dir=Path("data"),
    to_s3=False,
)
    
@cli.command()
def etl():
    rag_etl(
        data_dir=Path("data"),
        load_collection_name="notion",
        to_s3=False,
        max_workers=10,
        quality_agent_model_id="gpt-4o-mini",
        quality_agent_mock=True,
    )


@cli.command()
def create_dataset():
    generate_dataset(
        extract_collection_name="notion",
        load_dataset_id="notion",
        fetch_limit=1000,
        summarization_agent_model_id="gpt-4o-mini",
        summarization_agent_mock=False,
        summarization_max_characters=256,
        val_split_ratio=0.3,
        test_split_ratio=0.1,
        min_document_characters=50,
    )

@cli.command()
def index():
    compute_rag_vector_index(
    extract_collection_name="notion",
    fetch_limit=1000,
    load_collection_name="rag",
    content_quality_score_threshold=0.3,
    retriever_type="parent",
    embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
    embedding_model_type="huggingface",
    embedding_model_dim=384,
    chunk_size=512,
    vectorstore="faiss",
    contextual_summarization_type="contextual",
    contextual_agent_model_id="gpt-4o-mini",
    contextual_agent_max_characters=1000,
    mock=True,
    device="cpu",
)
    
@cli.command()
@click.option(
    "--retriever-config-path",
    type=click.Path(exists=True),
    required=True,
    default=Path(__file__).parent / "config/compute_rag_vector_index_openai_contextual_simple.yaml",
    help="Path to the retriever config file",
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
def chat(retriever_config_path, ui, query):
    agent = get_agent(Path(retriever_config_path))
    if ui:
        GradioUI(agent).launch()
    else:
        assert query, "Query is required in CLI mode"
        result = agent.run(query)
        print(result)



if __name__ == "__main__":
    cli()