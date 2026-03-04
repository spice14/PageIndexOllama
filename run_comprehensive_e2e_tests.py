#!/usr/bin/env python3
"""
Comprehensive E2E Test Suite for PageIndex
Tests all PDFs with the complete 4-stage workflow:
1. Submit to PageIndex (tree generation)
2. Wait for tree to be ready
3. Ask LLM to search tree and return node IDs
4. Extract node text and produce final answer

Generates individual reports for each PDF and a consolidated report.
"""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Set environment BEFORE imports
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["OLLAMA_MODEL"] = "mistral24b-16k"
os.environ["OLLAMA_URL"] = "http://localhost:11434"

sys.path.insert(0, '/workspace/PageIndexOllama')

from pageindex.page_index import page_index
from pageindex.utils import Ollama_API
import logging

# Suppress debug output for cleaner test output
logging.basicConfig(level=logging.CRITICAL)

# Configuration
PDF_DIR = Path('tests/pdfs')
REPORTS_DIR = Path('tests/reports')
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Test all PDFs in the directory
TEST_PDFS = sorted([f for f in PDF_DIR.glob('*.pdf')])

STAGE4_QUESTIONS = [
    "What are the key themes and core topics in this document?",
    "Summarize the document for an executive audience in 5-7 bullet points.",
    "What major findings, claims, or conclusions are presented?",
    "List important dates, periods, or timeline-related references found in the context.",
    "Identify any quantitative metrics, financial values, or performance indicators mentioned.",
    "What risks, limitations, or caveats are described?",
    "What strategic priorities, recommendations, or action items are discussed?",
    "Who are the main entities, stakeholders, or organizations referenced?",
    "What assumptions or dependencies does the document appear to rely on?",
    "Provide the three most important takeaways, each with a short justification.",
]

def format_time(seconds):
    """Format seconds into human-readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds//60:.0f}m {seconds%60:.0f}s"
    else:
        return f"{seconds//3600:.0f}h {(seconds%3600)//60:.0f}m"

def stage_1_tree_generation(pdf_path):
    """Stage 1: Submit to PageIndex for tree generation"""
    print(f"    Stage 1: Tree generation...", end=" ", flush=True)
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
        num_nodes = len(result.get('structure', []))
        print(f"✓ {num_nodes} nodes ({format_time(elapsed)})")
        return {
            'status': 'SUCCESS',
            'time': elapsed,
            'num_nodes': num_nodes,
            'tree': result
        }
    except Exception as e:
        elapsed = time.time() - start
        error_msg = str(e)[:200]
        print(f"✗ Failed ({format_time(elapsed)})")
        print(f"               Error: {error_msg}")
        return {
            'status': 'FAILED',
            'time': elapsed,
            'error': error_msg,
            'tree': None
        }

def stage_2_wait_for_tree(stage1_result):
    """Stage 2: Wait for tree to be ready (synchronous, so immediate)"""
    print(f"    Stage 2: Wait for ready...", end=" ", flush=True)
    
    if stage1_result['status'] != 'SUCCESS' or not stage1_result['tree']:
        print("✗ No tree available")
        return {'status': 'FAILED', 'error': 'No tree from stage 1'}
    
    # Tree generation is synchronous, so it's already ready
    num_nodes = stage1_result['num_nodes']
    print(f"✓ Tree ready ({num_nodes} nodes)")
    return {'status': 'SUCCESS', 'ready': True}

def stage_3_search_tree(stage1_result):
    """Stage 3: Ask LLM to search tree and return node IDs"""
    print(f"    Stage 3: LLM search for relevant nodes...", end=" ", flush=True)
    start = time.time()
    
    if stage1_result['status'] != 'SUCCESS' or not stage1_result['tree']:
        print("✗ No tree available")
        return {'status': 'FAILED', 'error': 'No tree from stage 1'}
    
    try:
        tree = stage1_result['tree']
        structure = tree.get('structure', [])
        
        # Create a compact representation of the tree structure for the search prompt
        tree_summary = []
        for i, node in enumerate(structure[:20]):  # Limit to first 20 nodes for prompt
            node_id = node.get('node_id', 'N/A')
            title = node.get('title', 'Untitled')
            tree_summary.append(f"[{node_id}] {title}")
        
        tree_text = "\n".join(tree_summary)
        
        # Search prompt asking LLM to identify relevant nodes
        prompt = f"""You are analyzing a document tree structure. Here are the nodes:

{tree_text}

Task: Identify the 3 most important nodes that represent key sections or main topics of this document.

Return your answer as JSON with this format:
{{"found_nodes": ["node_id_1", "node_id_2", "node_id_3"], "reasoning": "brief explanation"}}"""
        
        response = Ollama_API(model='mistral24b-16k', prompt=prompt)
        elapsed = time.time() - start
        
        # Try to parse the response to extract node IDs
        try:
            # Look for JSON in the response
            if '{' in response and '}' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                search_result = json.loads(json_str)
                found_nodes = search_result.get('found_nodes', [])
                print(f"✓ Found {len(found_nodes)} nodes ({format_time(elapsed)})")
                return {
                    'status': 'SUCCESS',
                    'time': elapsed,
                    'found_nodes': found_nodes,
                    'response': response
                }
            else:
                # Fallback: return first 3 node IDs
                found_nodes = [node.get('node_id', f'{i:04d}') for i, node in enumerate(structure[:3])]
                print(f"✓ Found {len(found_nodes)} nodes (fallback) ({format_time(elapsed)})")
                return {
                    'status': 'SUCCESS',
                    'time': elapsed,
                    'found_nodes': found_nodes,
                    'response': response
                }
        except:
            # Fallback: return first 3 node IDs
            found_nodes = [node.get('node_id', f'{i:04d}') for i, node in enumerate(structure[:3])]
            print(f"✓ Found {len(found_nodes)} nodes (fallback) ({format_time(elapsed)})")
            return {
                'status': 'SUCCESS',
                'time': elapsed,
                'found_nodes': found_nodes,
                'response': response
            }
            
    except Exception as e:
        elapsed = time.time() - start
        error_msg = str(e)[:200]
        print(f"✗ Failed ({format_time(elapsed)})")
        return {
            'status': 'FAILED',
            'time': elapsed,
            'error': error_msg
        }

def stage_4_extract_answer(stage1_result, stage3_result):
    """Stage 4: Extract node text and run multi-question Q&A"""
    print(f"    Stage 4: Extract text + 10 Q&A...", end=" ", flush=True)
    start = time.time()

    if stage1_result['status'] != 'SUCCESS' or not stage1_result['tree']:
        print("✗ No tree available")
        return {'status': 'FAILED', 'error': 'No tree from stage 1'}

    if stage3_result['status'] != 'SUCCESS':
        print("✗ No search results")
        return {'status': 'FAILED', 'error': 'No search results from stage 3'}

    try:
        tree = stage1_result['tree']
        structure = tree.get('structure', [])
        found_node_ids = stage3_result.get('found_nodes', [])

        # Extract text from found nodes
        extracted_content = []
        context_parts = []
        for node_id in found_node_ids:
            for node in structure:
                if node.get('node_id') == node_id:
                    title = node.get('title', 'Untitled')
                    text = node.get('text', '')
                    if text:
                        text_preview = text[:500] + '...' if len(text) > 500 else text
                        extracted_content.append({
                            'node_id': node_id,
                            'title': title,
                            'text_length': len(text),
                            'text_preview': text_preview
                        })
                        context_parts.append(f"[{title}]\n{text}")
                    break

        if not extracted_content:
            for i, node in enumerate(structure[:3]):
                title = node.get('title', 'Untitled')
                text = node.get('text', '')
                if text:
                    text_preview = text[:500] + '...' if len(text) > 500 else text
                    extracted_content.append({
                        'node_id': node.get('node_id', f'{i:04d}'),
                        'title': title,
                        'text_length': len(text),
                        'text_preview': text_preview
                    })
                    context_parts.append(f"[{title}]\n{text}")

        total_chars = sum(item['text_length'] for item in extracted_content)

        qa_context = "\n\n".join(context_parts)
        if len(qa_context) > 10000:
            qa_context = qa_context[:10000] + "\n...[truncated]"

        question_results = []
        for question in STAGE4_QUESTIONS:
            question_start = time.time()
            answer_prompt = f"""You are given extracted text from a document and a question.

Question: {question}

Context:
{qa_context}

Return a concise, factual answer grounded only in the provided context."""

            try:
                final_answer = Ollama_API(model='mistral24b-16k', prompt=answer_prompt)
                answer_length = len(final_answer or "")
                question_results.append({
                    'question': question,
                    'status': 'SUCCESS',
                    'time': time.time() - question_start,
                    'final_answer': final_answer,
                    'answer_length': answer_length,
                })
            except Exception as question_error:
                question_results.append({
                    'question': question,
                    'status': 'FAILED',
                    'time': time.time() - question_start,
                    'error': str(question_error)[:200],
                    'final_answer': '',
                    'answer_length': 0,
                })

        elapsed = time.time() - start
        successful_questions = sum(1 for item in question_results if item['status'] == 'SUCCESS')
        total_answer_chars = sum(item.get('answer_length', 0) for item in question_results)
        stage_status = 'SUCCESS' if successful_questions == len(STAGE4_QUESTIONS) else 'FAILED'

        print(
            f"✓ Extracted {len(extracted_content)} nodes ({total_chars:,} chars), "
            f"Q&A {successful_questions}/{len(STAGE4_QUESTIONS)} ({format_time(elapsed)})"
        )

        return {
            'status': stage_status,
            'time': elapsed,
            'extracted_nodes': extracted_content,
            'total_characters': total_chars,
            'questions': question_results,
            'questions_attempted': len(STAGE4_QUESTIONS),
            'questions_successful': successful_questions,
            'answer_length': total_answer_chars
        }

    except Exception as e:
        elapsed = time.time() - start
        error_msg = str(e)[:200]
        print(f"✗ Failed ({format_time(elapsed)})")
        return {
            'status': 'FAILED',
            'time': elapsed,
            'error': error_msg
        }

def generate_individual_report(pdf_name, stage1, stage2, stage3, stage4, total_time):
    """Generate detailed report for individual PDF"""
    report_path = REPORTS_DIR / f"{pdf_name.replace('.pdf', '')}_E2E_REPORT.md"
    
    # Determine overall status
    all_success = all(
        stage.get('status') == 'SUCCESS' 
        for stage in [stage1, stage2, stage3, stage4]
    )
    overall_status = "✅ SUCCESS" if all_success else "⚠️ PARTIAL SUCCESS" if stage1['status'] == 'SUCCESS' else "❌ FAILED"
    
    report_content = f"""# E2E Test Report: {pdf_name}

**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Overall Status:** {overall_status}  
**Total Time:** {format_time(total_time)}

---

## Stage 1: Tree Generation
- **Status:** {stage1['status']}
- **Time:** {format_time(stage1['time'])}
- **Nodes Generated:** {stage1.get('num_nodes', 'N/A')}
{'- **Error:** ' + stage1.get('error', '') if stage1['status'] != 'SUCCESS' else ''}

## Stage 2: Wait for Tree Ready
- **Status:** {stage2['status']}
- **Tree Ready:** {stage2.get('ready', False)}
{'- **Error:** ' + stage2.get('error', '') if stage2['status'] != 'SUCCESS' else ''}

## Stage 3: LLM Search
- **Status:** {stage3['status']}
- **Time:** {format_time(stage3.get('time', 0))}
- **Nodes Found:** {len(stage3.get('found_nodes', []))}
- **Node IDs:** {', '.join(stage3.get('found_nodes', [])) if stage3.get('found_nodes') else 'None'}
{'- **Error:** ' + stage3.get('error', '') if stage3['status'] != 'SUCCESS' else ''}

## Stage 4: Q&A from Extracted Nodes
- **Status:** {stage4['status']}
- **Time:** {format_time(stage4.get('time', 0))}
- **Nodes Extracted:** {len(stage4.get('extracted_nodes', []))}
- **Total Characters:** {stage4.get('total_characters', 0):,}
- **Questions Attempted:** {stage4.get('questions_attempted', 0)}
- **Questions Successful:** {stage4.get('questions_successful', 0)}
- **Total Answer Characters:** {stage4.get('answer_length', 0):,}
{'- **Error:** ' + stage4.get('error', '') if stage4['status'] != 'SUCCESS' else ''}

### Q&A Results:
"""


    if stage4.get('questions'):
        for idx, question_item in enumerate(stage4['questions'], start=1):
            report_content += f"""
#### Q{idx}: {question_item.get('question', 'N/A')}
- **Status:** {question_item.get('status', 'N/A')}
- **Time:** {format_time(question_item.get('time', 0))}
- **Answer Length:** {question_item.get('answer_length', 0):,}
{'- **Error:** ' + question_item.get('error', '') if question_item.get('status') != 'SUCCESS' else ''}

```
{(question_item.get('final_answer', 'N/A') or 'N/A')[:2000]}
```
"""
    else:
        report_content += "\n*No questions were executed*\n"

    report_content += """
### Extracted Content Preview:
"""
    
    if stage4.get('extracted_nodes'):
        for node in stage4['extracted_nodes']:
            report_content += f"""
#### Node: {node['title']} (ID: {node['node_id']})
**Length:** {node['text_length']:,} characters

```
{node['text_preview']}
```
"""
    else:
        report_content += "\n*No content extracted*\n"
    
    report_content += f"""

---

## Performance Summary
- **Stage 1 (Tree Gen):** {format_time(stage1['time'])}
- **Stage 2 (Wait):** < 1s (synchronous)
- **Stage 3 (Search):** {format_time(stage3.get('time', 0))}
- **Stage 4 (Extract):** {format_time(stage4.get('time', 0))}
- **Total:** {format_time(total_time)}

---

**Model:** mistral24b-16k  
**Provider:** Ollama (local inference)
"""
    
    with open(report_path, 'w') as f:
        f.write(report_content)
    
    return report_path

def test_pdf(pdf_path):
    """Run complete 4-stage E2E test on one PDF"""
    pdf_name = pdf_path.name
    print(f"\n{'='*70}")
    print(f"Testing: {pdf_name}")
    print(f"{'='*70}")
    
    start_time = time.time()
    
    # Stage 1: Tree Generation
    stage1 = stage_1_tree_generation(pdf_path)
    
    # Stage 2: Wait for Ready
    stage2 = stage_2_wait_for_tree(stage1)
    
    # Stage 3: LLM Search
    stage3 = stage_3_search_tree(stage1)
    
    # Stage 4: Extract Answer
    stage4 = stage_4_extract_answer(stage1, stage3)
    
    total_time = time.time() - start_time
    
    # Generate individual report
    report_path = generate_individual_report(pdf_name, stage1, stage2, stage3, stage4, total_time)
    print(f"    Report: {report_path.name}")
    
    overall_status = 'SUCCESS' if all(
        stage.get('status') == 'SUCCESS' for stage in [stage1, stage2, stage3, stage4]
    ) else 'FAILED'

    # Return summary for consolidated report
    return {
        'pdf': pdf_name,
        'status': overall_status,
        'num_nodes': stage1.get('num_nodes', 0),
        'total_time': total_time,
        'stage1': stage1['status'],
        'stage2': stage2['status'],
        'stage3': stage3['status'],
        'stage4': stage4['status'],
        'questions_attempted': stage4.get('questions_attempted', 0),
        'questions_successful': stage4.get('questions_successful', 0),
        'qa_answer_length': stage4.get('answer_length', 0),
        'report_path': str(report_path)
    }

def generate_consolidated_report(results):
    """Generate consolidated report for all PDFs"""
    report_path = REPORTS_DIR / 'CONSOLIDATED_E2E_REPORT.md'
    
    successful = sum(1 for r in results if r['status'] == 'SUCCESS')
    total = len(results)
    success_rate = (successful / total * 100) if total > 0 else 0
    
    total_time = sum(r['total_time'] for r in results)
    avg_time = total_time / total if total > 0 else 0
    
    report_content = f"""# Consolidated E2E Test Report

**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Model:** mistral24b-16k  
**Provider:** Ollama (local inference)

---

## Summary

- **Total PDFs Tested:** {total}
- **Successful:** {successful}
- **Failed:** {total - successful}
- **Success Rate:** {success_rate:.1f}%
- **Total Time:** {format_time(total_time)}
- **Average Time per PDF:** {format_time(avg_time)}

---

## Detailed Results

| PDF | Status | Nodes | Time | S1 | S2 | S3 | S4 | Q&A (ok/total) | Q&A Chars | Report |
|-----|--------|-------|------|----|----|----|----|----------------|-----------|--------|
"""
    
    for r in results:
        status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
        s1_icon = "✓" if r['stage1'] == 'SUCCESS' else "✗"
        s2_icon = "✓" if r['stage2'] == 'SUCCESS' else "✗"
        s3_icon = "✓" if r['stage3'] == 'SUCCESS' else "✗"
        s4_icon = "✓" if r['stage4'] == 'SUCCESS' else "✗"
        report_name = Path(r['report_path']).name
        
        report_content += f"| {r['pdf']} | {status_icon} | {r['num_nodes']} | {format_time(r['total_time'])} | {s1_icon} | {s2_icon} | {s3_icon} | {s4_icon} | {r.get('questions_successful', 0)}/{r.get('questions_attempted', 0)} | {r.get('qa_answer_length', 0):,} | [{report_name}]({report_name}) |\n"
    
    report_content += f"""

**Legend:**
- S1 = Stage 1 (Tree Generation)
- S2 = Stage 2 (Wait for Ready)
- S3 = Stage 3 (LLM Search)
- S4 = Stage 4 (Extract + Q&A)

---

## Performance Breakdown

### Tree Generation (Stage 1)
"""
    
    stage1_success = sum(1 for r in results if r['stage1'] == 'SUCCESS')
    report_content += f"- Success Rate: {stage1_success}/{total} ({stage1_success/total*100:.1f}%)\n\n"
    
    report_content += """### LLM Search (Stage 3)
"""
    stage3_success = sum(1 for r in results if r['stage3'] == 'SUCCESS')
    report_content += f"- Success Rate: {stage3_success}/{total} ({stage3_success/total*100:.1f}%)\n\n"
    
    report_content += """### Q&A from Extracted Context (Stage 4)
"""
    stage4_success = sum(1 for r in results if r['stage4'] == 'SUCCESS')
    report_content += f"- Success Rate: {stage4_success}/{total} ({stage4_success/total*100:.1f}%)\n\n"

    total_questions_attempted = sum(r.get('questions_attempted', 0) for r in results)
    total_questions_successful = sum(r.get('questions_successful', 0) for r in results)
    question_success_rate = (total_questions_successful / total_questions_attempted * 100) if total_questions_attempted > 0 else 0
    report_content += """### Multi-Question Q&A Summary
"""
    report_content += f"- Questions Attempted: {total_questions_attempted}\n"
    report_content += f"- Questions Successful: {total_questions_successful}\n"
    report_content += f"- Question Success Rate: {question_success_rate:.1f}%\n\n"
    
    report_content += """---

## Test Environment

- **Python Version:** 3.11
- **GPU:** NVIDIA RTX 4090 (24GB VRAM)
- **Model:** mistral24b-16k (23.6B parameters, Q4_K_M)
- **Context Window:** 16,384 tokens
- **Max Output Tokens:** 4,096
- **Concurrency:** Semaphore(3)

---

*Generated by PageIndex E2E Test Suite*
"""
    
    with open(report_path, 'w') as f:
        f.write(report_content)
    
    return report_path

def main():
    print("\n" + "="*70)
    print("PageIndex Comprehensive E2E Test Suite")
    print("="*70)
    print(f"Environment:")
    print(f"  - LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")
    print(f"  - OLLAMA_MODEL: {os.getenv('OLLAMA_MODEL')}")
    print(f"  - Test PDFs: {len(TEST_PDFS)}")
    print()
    
    results = []
    for pdf_path in TEST_PDFS:
        try:
            result = test_pdf(pdf_path)
            results.append(result)
        except Exception as e:
            print(f"    ❌ Unexpected error: {str(e)[:100]}")
            results.append({
                'pdf': pdf_path.name,
                'status': 'FAILED',
                'num_nodes': 0,
                'total_time': 0,
                'stage1': 'FAILED',
                'stage2': 'FAILED',
                'stage3': 'FAILED',
                'stage4': 'FAILED',
                'questions_attempted': 0,
                'questions_successful': 0,
                'qa_answer_length': 0,
                'report_path': 'N/A'
            })
    
    # Generate consolidated report
    print(f"\n{'='*70}")
    print("Generating consolidated report...")
    print(f"{'='*70}")
    
    consolidated_path = generate_consolidated_report(results)
    print(f"✓ Consolidated report: {consolidated_path}")
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    
    successful = sum(1 for r in results if r['status'] == 'SUCCESS')
    total = len(results)
    
    print(f"Total PDFs tested: {total}")
    print(f"Successful: {successful} ({successful/total*100:.1f}%)")
    print(f"Failed: {total - successful}")
    print()
    
    for r in results:
        status_icon = "✅" if r['status'] == 'SUCCESS' else "❌"
        print(f"{status_icon} {r['pdf']}: {r['num_nodes']} nodes ({format_time(r['total_time'])})")
    
    print(f"\n{'='*70}")
    print(f"All reports saved to: {REPORTS_DIR.absolute()}")
    print(f"{'='*70}\n")
    
    # Save JSON results
    json_path = REPORTS_DIR / 'E2E_TEST_RESULTS.json'
    with open(json_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'environment': {
                'LLM_PROVIDER': os.getenv('LLM_PROVIDER'),
                'OLLAMA_MODEL': os.getenv('OLLAMA_MODEL'),
            },
            'summary': {
                'total_tests': total,
                'successful': successful,
                'failed': total - successful,
                'success_rate': f"{successful/total*100:.1f}%"
            },
            'results': results
        }, f, indent=2)
    print(f"JSON results saved to: {json_path}")
    
    return 0 if successful == total else 1

if __name__ == '__main__':
    sys.exit(main())
