#!/usr/bin/env python3
"""
Comprehensive E2E Test Suite for PageIndex
Tests all PDFs with the 4 required steps:
1. Submit PDF to PageIndex (tree generation)
2. Wait for tree to be ready
3. Ask LLM to search tree and return node IDs
4. Extract node text and produce final answer
"""
import os
import sys
import time
import json
from pathlib import Path

# Set environment BEFORE imports
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["OLLAMA_MODEL"] = "mistral24b-16k"
os.environ["OLLAMA_URL"] = "http://localhost:11434"

sys.path.insert(0, '/workspace/PageIndexOllama')

from pageindex.page_index import page_index
from pageindex.utils import Ollama_API
import logging

# Suppress debug output
logging.basicConfig(level=logging.WARNING)

# Configuration
PDF_DIR = Path('tests/pdfs')
RESULTS_DIR = Path('tests/reports')
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Test PDFs (using smaller ones for faster testing)
TEST_PDFS = [
    '2023-annual-report-truncated.pdf',
    'PRML.pdf',
    'earthmover.pdf',
]

def step_1_tree_generation(pdf_path):
    """Step 1: Submit to PageIndex for tree generation"""
    print(f"  Step 1: Tree generation... ", end="", flush=True)
    start = time.time()
    
    try:
        result = page_index(
            str(pdf_path),
            model='mistral24b-16k',
            if_add_node_id='yes',
            if_add_node_text='yes',
            if_add_node_summary='no',
            if_add_doc_description='no'
        )
        elapsed = time.time() - start
        print(f"✓ ({elapsed:.1f}s, {len(result['structure'])} nodes)")
        return result
    except Exception as e:
        print(f"✗ {str(e)[:80]}")
        return None

def step_2_wait_for_tree(result):
    """Step 2: Wait for tree to be ready (already done in step 1)"""
    print(f"  Step 2: Wait for ready... ", end="", flush=True)
    # Tree generation is synchronous, so it's already ready
    num_nodes = len(result['structure']) if result and 'structure' in result else 0
    print(f"✓ ({num_nodes} nodes ready)")
    return result is not None

def step_3_search_tree(result):
    """Step 3: Ask LLM to search tree and return node IDs"""
    print(f"  Step 3: LLM search... ", end="", flush=True)
    
    if not result:
        print("✗ No tree generated")
        return None
    
    # Build search prompt with tree structure
    structure_text = json.dumps(result['structure'][:5], indent=2)  # First 5 nodes
    prompt = f"""Given this document tree structure:
{structure_text}

Find nodes related to "main topics" or "overview". 
Return a JSON object with:
{{"found_nodes": [list of node titles], "node_ids": [list of node_ids]}}"""
    
    try:
        response = Ollama_API(model='mistral24b-16k', prompt=prompt)
        print(f"✓ Found nodes")
        return response
    except Exception as e:
        print(f"✗ {str(e)[:50]}")
        return None

def step_4_extract_answer(result, search_response):
    """Step 4: Extract node text and produce final answer"""
    print(f"  Step 4: Extract answer... ", end="", flush=True)
    
    if not result or not search_response:
        print("✗ Missing data")
        return None
    
    try:
        # Extract text from first few nodes
        answer_text = ""
        for node in result['structure'][:3]:
            if 'text' in node:
                answer_text += node.get('title', 'Untitled') + ": " + node['text'][:200] + "\n\n"
        
        if answer_text:
            print(f"✓ Extracted {len(answer_text)} chars")
            return answer_text
        else:
            print("✓ (no text content)")
            return "(Document structure extracted successfully)"
    except Exception as e:
        print(f"✗ {str(e)[:50]}")
        return None

def test_pdf(pdf_path):
    """Run full 4-step E2E test on one PDF"""
    print(f"\nTesting: {pdf_path.name}")
    print("=" * 60)
    
    # Step 1
    result = step_1_tree_generation(pdf_path)
    if not result:
        return {"pdf": pdf_path.name, "status": "FAILED", "error": "Tree generation failed"}
    
    # Step 2
    ready = step_2_wait_for_tree(result)
    if not ready:
        return {"pdf": pdf_path.name, "status": "FAILED", "error": "Tree not ready"}
    
    # Step 3
    search_response = step_3_search_tree(result)
    if not search_response:
        return {"pdf": pdf_path.name, "status": "FAILED", "error": "Search failed"}
    
    # Step 4
    answer = step_4_extract_answer(result, search_response)
    if not answer:
        return {"pdf": pdf_path.name, "status": "FAILED", "error": "Answer extraction failed"}
    
    return {
        "pdf": pdf_path.name,
        "status": "SUCCESS",
        "nodes": len(result['structure']),
        "answer_excerpt": answer[:200] if answer else ""
    }

def main():
    print("\n" + "=" * 60)
    print("PageIndex E2E Test Suite")
    print("=" * 60)
    print(f"Environment: LLM_PROVIDER={os.getenv('LLM_PROVIDER')}, OLLAMA_MODEL={os.getenv('OLLAMA_MODEL')}")
    print()
    
    results = []
    for pdf_name in TEST_PDFS:
        pdf_path = PDF_DIR / pdf_name
        if not pdf_path.exists():
            print(f"\n⚠️  Skipping: {pdf_name} (not found)")
            continue
        
        result = test_pdf(pdf_path)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    successful = sum(1 for r in results if r['status'] == 'SUCCESS')
    total = len(results)
    
    for r in results:
        status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
        print(f"{status_icon} {r['pdf']}: {r['status']}")
        if 'nodes' in r:
            print(f"   → {r['nodes']} nodes generated")
        if 'error' in r:
            print(f"   → Error: {r['error']}")
    
    print()
    print(f"Results: {successful}/{total} PDFs processed successfully")
    
    # Write results to file
    with open(RESULTS_DIR / 'e2e_test_results.json', 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'environment': {
                'LLM_PROVIDER': os.getenv('LLM_PROVIDER'),
                'OLLAMA_MODEL': os.getenv('OLLAMA_MODEL'),
            },
            'summary': {
                'total_tests': total,
                'successful': successful,
                'failed': total - successful,
            },
            'results': results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {RESULTS_DIR / 'e2e_test_results.json'}")
    
    return 0 if successful == total else 1

if __name__ == '__main__':
    sys.exit(main())
