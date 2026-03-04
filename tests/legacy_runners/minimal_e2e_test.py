#!/usr/bin/env python3
"""
Minimal E2E test for tree generation
"""
import os
import sys

# Set environment BEFORE imports
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["OLLAMA_MODEL"] = "mistral24b-16k"
os.environ["OLLAMA_URL"] = "http://localhost:11434"

sys.path.insert(0, '/workspace/PageIndexOllama')

from pageindex.page_index import page_index
import logging

# Suppress debug output
logging.basicConfig(level=logging.WARNING)

print("Testing single tree generation...")
print("Model: mistral24b-16k")
print("PDF: 2023-annual-report-truncated.pdf (50 pages)")
print()

result = page_index(
    'tests/pdfs/2023-annual-report-truncated.pdf',
    model='mistral24b-16k',  # Explicitly pass model
    if_add_node_id='yes',
    if_add_node_text='no',
    if_add_node_summary='no',
    if_add_doc_description='no'
)

print("✅ SUCCESS!")
print(f"Document: {result['doc_name']}")
print(f"Nodes: {len(result['structure'])}")
for i, node in enumerate(result['structure'][:5]):
    print(f"  {i+1}. {node.get('title','')} [ID:{node.get('node_id','')}]")
