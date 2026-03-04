#!/usr/bin/env python3
"""
Quick test script for tree generation with fixed configuration.
"""
import sys
import os

# Set environment before imports
os.environ['LLM_PROVIDER'] = 'ollama'
os.environ['OLLAMA_MODEL'] = 'mistral24b-16k'
os.environ['OLLAMA_URL'] = 'http://localhost:11434'

sys.path.insert(0, '/workspace/PageIndexOllama')

from pageindex import page_index

print('='*60)
print('Testing Tree Generation')
print('='*60)
print(f'LLM_PROVIDER: {os.getenv("LLM_PROVIDER")}')
print(f'OLLAMA_MODEL: {os.getenv("OLLAMA_MODEL")}')
print(f'OLLAMA_URL: {os.getenv("OLLAMA_URL")}')
print('='*60)
print()

print('Processing: tests/pdfs/2023-annual-report-truncated.pdf')
print('Please wait...\n')

result = page_index(
    'tests/pdfs/2023-annual-report-truncated.pdf',
    if_add_node_id='yes',
    if_add_node_text='no',
    if_add_node_summary='no',
    if_add_doc_description='no'
)

print('\n' + '='*60)
print('✅ TREE GENERATION SUCCESSFUL!')
print('='*60)
print(f'Document: {result["doc_name"]}')
print(f'Top-level nodes: {len(result["structure"])}')
print()
print('First 5 nodes:')
for i, node in enumerate(result['structure'][:5]):
    title = node.get('title', '(no title)')
    node_id = node.get('node_id', 'N/A')
    print(f'  {i+1}. {title[:60]}... [ID: {node_id}]')
print('='*60)
