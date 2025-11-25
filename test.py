from src.vectorstore.metadata_mapper import MetadataMapper
from config.settings import get_vectorstore_config

config = get_vectorstore_config()
mapper = MetadataMapper()
mapper.load(str(config.metadata_path))

# Vedi tutti i topics disponibili
all_topics = set()
for doc_id, doc in mapper.get_all_documents().items():
    if isinstance(doc, dict):
        bm = doc.get('bloomberg_metadata', {})
        if isinstance(bm, dict) and bm.get('topics'):
            all_topics.update(bm['topics'])
    
print("Topics disponibili:", sorted(all_topics))