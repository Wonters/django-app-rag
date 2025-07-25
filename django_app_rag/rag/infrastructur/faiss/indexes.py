from pathlib import Path

class FaissDBIndex:
    persist_dir: Path = Path("faiss_index")

    def __init__(self, retriever, **kwargs) -> None:
        self.retriever = retriever

    def create(self, embedding_dim: int, is_hybrid: bool = False) -> None:
        """"""
        vectorstore = self.retriever.vectorstore
