from django_app_rag.rag.infrastructur.disk_storage import DiskStorage
from django_app_rag.rag.retrievers import get_retriever
import pprint
disk_storage = DiskStorage(
    collection_name="Low_Tech_1",
    data_dir="../media/rag_data/1",
)

# documents = disk_storage.read_raw()
# print(len(documents))
# print(len(set([doc["id"] for doc in documents])))
#pprint.pprint([doc["metadata"] for doc in documents if doc["content_quality_score"] > 0.8])

# document  = disk_storage.read(ids_documents=["hAA7yaOmobLimxISk3jTKEEFtpvE_Z9e"])

vector_storage = get_retriever(
    embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
    embedding_model_type="huggingface",
    retriever_type="parent",
    k=3,
    device="cpu",
    vectorstore="faiss",
    persistent_path="../media/rag_data/1",
)

print("\n=== Test avec le retriever complet ===")
rep2 = vector_storage.invoke("Comment faire une lessive au lierre ?")
print(f"Nombre de documents trouvés: {len(rep2)}")
for i, doc in enumerate(rep2):
    print(f"Document {i+1}:")
    print(f"  ID: {doc.metadata.get('id', 'N/A')}")
    print(f"  Score: {doc.metadata.get('similarity_score', 'N/A')}")
    print(f"  Contenu: {doc.page_content[:200]}...")
    print(f"  URL: {doc.metadata.get('url', 'N/A')}")
    print()