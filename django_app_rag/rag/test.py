from django_app_rag.rag.infrastructur.disk_storage import DiskStorage
from django_app_rag.rag.models import Document
from django_app_rag.rag.retrievers import get_retriever
def test_disk_storage():
    storage = DiskStorage(model_class=Document, collection_name="notion")
    documents = storage.read()

    print(documents)


def test_retriever():
    retriever = get_retriever(
        embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
        embedding_model_type="huggingface",
        retriever_type="parent",
        k=3,
        device="cpu",
        vectorstore="faiss"
    )
    retriever.vectorstore.f

    documents = retriever.invoke(query="panneaux solaire")
    print(documents)

