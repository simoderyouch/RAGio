from langchain.embeddings.base import Embeddings

class CustomEmbedding(Embeddings):
    def __init__(self, model):
        self.model = model

    def embed_documents(self, texts):
        return [self.model.encode(text, convert_to_tensor=True).cpu().numpy() for text in texts]

    def embed_query(self, text):
        return self.model.encode(text, convert_to_tensor=True).cpu().numpy().tolist()
