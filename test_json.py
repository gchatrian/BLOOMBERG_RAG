import json
from pathlib import Path

# Leggi il JSON direttamente
json_path = Path("data/documents_metadata.json")
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Mostra struttura di un documento
print(f"Totale documenti: {len(data)}")
print(f"\nChiavi nel JSON: {list(data.keys())[:5]}")

# Prendi il primo documento
first_key = list(data.keys())[0]
first_doc = data[first_key]

print(f"\nDocumento {first_key}:")
print(f"  Tipo: {type(first_doc)}")
if isinstance(first_doc, dict):
    print(f"  Chiavi: {list(first_doc.keys())}")
    if 'bloomberg_metadata' in first_doc:
        bm = first_doc['bloomberg_metadata']
        print(f"  bloomberg_metadata tipo: {type(bm)}")
        if isinstance(bm, dict):
            print(f"  bloomberg_metadata chiavi: {list(bm.keys())}")
            print(f"  topics: {bm.get('topics')}")
            print(f"  people: {bm.get('people')}")