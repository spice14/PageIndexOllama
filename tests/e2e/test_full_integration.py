#!/usr/bin/env python3
"""
Full End-to-End Test for PageIndex with Ollama
Tests all 5 functional steps:
1. Download PDF (or use existing)
2. Submit to PageIndex (tree generation)
3. Wait for tree to be ready
4. Query tree with LLM for node IDs
5. Extract node text and produce final answer
"""

import json
import sys
import time
import asyncio
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add pageindex to path
sys.path.insert(0, str(Path(__file__).parent))

from pageindex import page_index_main
from pageindex.utils import ChatGPT_API, count_tokens
from pageindex.model_capabilities import get_model_capabilities


class E2ETestRunner:
    """End-to-end test runner for PageIndex"""
    
    def __init__(self, pdf_path: str, model: str = "mistral:7b"):
        self.pdf_path = pdf_path
        self.model = model
        self.start_time = None
        self.results = {
            "pdf_file": Path(pdf_path).name,
            "model_used": model,
            "timestamp": datetime.now().isoformat(),
            "steps": {}
        }
        
        # Verify model capabilities
        self.capabilities = get_model_capabilities(model)
        logger.info(f"Using model: {model}")
        logger.info(f"  Context window: {self.capabilities.context_window} tokens")
        logger.info(f"  Supports streaming: {self.capabilities.supports_streaming}")
        
    def run(self) -> Dict[str, Any]:
        """Run full E2E test"""
        self.start_time = time.time()
        
        try:
            # Step 1: Verify PDF exists
            logger.info("\n" + "="*80)
            logger.info("STEP 1: Verify PDF Download")
            logger.info("="*80)
            self._step1_verify_pdf()
            
            # Step 2: Generate Tree
            logger.info("\n" + "="*80)
            logger.info("STEP 2: Submit to PageIndex (Tree Generation)")
            logger.info("="*80)
            tree_data = self._step2_generate_tree()
            
            # Step 3: Verify Tree Ready
            logger.info("\n" + "="*80)
            logger.info("STEP 3: Tree Ready Verification")
            logger.info("="*80)
            self._step3_verify_tree_ready(tree_data)
            
            # Step 4: Query Tree with LLM
            logger.info("\n" + "="*80)
            logger.info("STEP 4: Query Tree & Get Node IDs")
            logger.info("="*80)
            node_ids = self._step4_query_tree_with_llm(tree_data)
            
            # Step 5: Extract and Answer
            logger.info("\n" + "="*80)
            logger.info("STEP 5: Extract Node Text & Final Answer")
            logger.info("="*80)
            final_answer = self._step5_extract_and_answer(tree_data, node_ids)
            
            # Finalize results
            self.results["status"] = "SUCCESS"
            self.results["total_duration_seconds"] = time.time() - self.start_time
            
            self._print_summary()
            return self.results
            
        except Exception as e:
            logger.error(f"E2E test failed: {e}", exc_info=True)
            self.results["status"] = "FAILED"
            self.results["error"] = str(e)
            self.results["total_duration_seconds"] = time.time() - self.start_time
            return self.results
    
    def _step1_verify_pdf(self):
        """Step 1: Verify PDF exists and get metadata"""
        step_start = time.time()
        
        if not Path(self.pdf_path).exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        
        pdf_info = {
            "file": Path(self.pdf_path).name,
            "path": str(Path(self.pdf_path).resolve()),
            "size_mb": Path(self.pdf_path).stat().st_size / (1024 * 1024),
            "exists": True
        }
        
        logger.info(f"✓ PDF file: {pdf_info['file']}")
        logger.info(f"  Location: {pdf_info['path']}")
        logger.info(f"  Size: {pdf_info['size_mb']:.2f} MB")
        
        self.results["steps"]["step_1_pdf_verification"] = {
            "duration_seconds": time.time() - step_start,
            "pdf_info": pdf_info
        }
    
    def _step2_generate_tree(self) -> Dict[str, Any]:
        """Step 2: Submit PDF to PageIndex and generate tree structure"""
        step_start = time.time()
        
        logger.info(f"Starting tree generation for: {Path(self.pdf_path).name}")
        
        try:
            # Create options for page_index_main
            from types import SimpleNamespace as config
            
            opt = config(
                model=self.model,
                toc_check_page_num=20,
                max_page_num_each_node=10,
                max_token_num_each_node=20000,
                if_add_node_id="yes",
                if_add_node_summary="yes",
                if_add_doc_description="yes",
                if_add_node_text="yes"
            )
            
            # Run page_index_main (synchronously - it handles async internally)
            logger.info("Extracting document structure...")
            tree_data = page_index_main(self.pdf_path, opt)
            
            logger.info(f"✓ Tree generation complete")
            logger.info(f"  Total nodes: {len(tree_data) if isinstance(tree_data, list) else 'N/A'}")
            
            tree_info = {
                "tree_type": type(tree_data).__name__,
                "nodes_count": len(tree_data) if isinstance(tree_data, list) else 1,
                "generation_time_seconds": time.time() - step_start
            }
            
            self.results["steps"]["step_2_tree_generation"] = {
                "duration_seconds": time.time() - step_start,
                "tree_info": tree_info,
                "sample_node": self._get_sample_node(tree_data)
            }
            
            return tree_data
            
        except Exception as e:
            logger.error(f"Tree generation failed: {e}")
            raise
    
    def _step3_verify_tree_ready(self, tree_data: Dict[str, Any]):
        """Step 3: Verify tree is ready - check structure integrity"""
        step_start = time.time()
        
        checks = {
            "tree_exists": tree_data is not None,
            "has_nodes": False,
            "nodes_have_content": False,
            "nodes_have_ids": False,
            "total_nodes": 0
        }
        
        if isinstance(tree_data, list):
            checks["has_nodes"] = len(tree_data) > 0
            checks["total_nodes"] = len(tree_data)
            
            # Sample check first few nodes
            for node in tree_data[:3]:
                if isinstance(node, dict):
                    checks["nodes_have_content"] = True
                    if "node_id" in node or "id" in node:
                        checks["nodes_have_ids"] = True
        
        logger.info(f"✓ Tree structure verification:")
        logger.info(f"  Tree exists: {checks['tree_exists']}")
        logger.info(f"  Has nodes: {checks['has_nodes']}")
        logger.info(f"  Total nodes: {checks['total_nodes']}")
        logger.info(f"  Nodes have content: {checks['nodes_have_content']}")
        logger.info(f"  Nodes have IDs: {checks['nodes_have_ids']}")
        
        self.results["steps"]["step_3_tree_ready"] = {
            "duration_seconds": time.time() - step_start,
            "checks": checks,
            "ready": all(checks.values())
        }
    
    def _step4_query_tree_with_llm(self, tree_data: Dict[str, Any]) -> List[str]:
        """Step 4: Query tree with LLM to identify relevant node IDs"""
        step_start = time.time()
        
        # Build tree summary for LLM
        tree_summary = self._build_tree_summary(tree_data)
        
        logger.info(f"Tree summary prepared ({len(tree_summary)} characters)")
        logger.info(f"Tokens in tree summary: {count_tokens(tree_summary, self.model, 'ollama')}")
        
        # Create query prompt
        query = """Given this document tree structure, identify the most important node IDs that answer these questions:
1. What is the main contribution or purpose of this document?
2. What are the key technical concepts introduced?
3. What is the methodology or approach used?

Return a JSON object with this format:
{
    "reasoning": "Brief explanation of why these nodes are important",
    "node_ids": ["id1", "id2", "id3", ...],
    "concepts": ["concept1", "concept2", ...]
}

TREE STRUCTURE:
""" + tree_summary
        
        logger.info("\nQuerying LLM to identify relevant nodes...")
        logger.info(f"Query length: {len(query)} characters")
        
        try:
            # Call LLM with tree query
            response = ChatGPT_API(
                model=self.model,
                prompt=query
            )
            
            logger.info(f"✓ LLM response received ({len(response)} characters)")
            
            # Try to parse JSON response
            node_ids = self._parse_llm_response(response)
            
            logger.info(f"\n✓ Identified {len(node_ids)} relevant nodes:")
            for nid in node_ids[:5]:  # Show first 5
                logger.info(f"  - {nid}")
            if len(node_ids) > 5:
                logger.info(f"  ... and {len(node_ids) - 5} more")
            
            self.results["steps"]["step_4_tree_query"] = {
                "duration_seconds": time.time() - step_start,
                "query_length": len(query),
                "response_length": len(response),
                "node_ids_found": len(node_ids),
                "llm_response_sample": response[:500]  # First 500 chars
            }
            
            return node_ids
            
        except Exception as e:
            logger.error(f"LLM tree query failed: {e}")
            raise
    
    def _step5_extract_and_answer(self, tree_data: Dict[str, Any], node_ids: List[str]) -> str:
        """Step 5: Extract node text and produce final answer"""
        step_start = time.time()
        
        logger.info(f"Extracting content from {len(node_ids)} nodes...")
        
        # Extract text from identified nodes
        extracted_content = self._extract_node_content(tree_data, node_ids)
        
        logger.info(f"✓ Extracted {len(extracted_content)} sections")
        logger.info(f"  Total content length: {sum(len(c.get('text', '')) for c in extracted_content)} characters")
        
        # Build final answer using extracted content
        synthesis_prompt = f"""Based on these extracted sections from the document, provide a comprehensive summary answering:
1. What is the main contribution of this document?
2. What are the key technical innovations?
3. Why is this important?

EXTRACTED SECTIONS:
"""
        
        for i, section in enumerate(extracted_content[:5], 1):  # Use first 5 sections
            synthesis_prompt += f"\n\n--- Section {i} (ID: {section.get('id', 'N/A')}) ---\n"
            synthesis_prompt += section.get('text', '')[:1000]  # Limit to 1000 chars per section
        
        logger.info("\nSynthesizing final answer from extracted content...")
        
        final_answer = ChatGPT_API(
            model=self.model,
            prompt=synthesis_prompt
        )
        
        logger.info(f"✓ Final answer synthesized ({len(final_answer)} characters)")
        logger.info("\n" + "="*80)
        logger.info("FINAL ANSWER")
        logger.info("="*80)
        logger.info(final_answer[:1000] + ("..." if len(final_answer) > 1000 else ""))
        
        self.results["steps"]["step_5_extraction_and_answer"] = {
            "duration_seconds": time.time() - step_start,
            "sections_extracted": len(extracted_content),
            "total_extracted_length": sum(len(c.get('text', '')) for c in extracted_content),
            "final_answer": final_answer
        }
        
        return final_answer
    
    def _build_tree_summary(self, tree_data: Dict[str, Any]) -> str:
        """Build a textual summary of the tree for LLM consumption"""
        summary = ""
        
        if isinstance(tree_data, list):
            for i, node in enumerate(tree_data[:20]):  # Limit to first 20 nodes
                if isinstance(node, dict):
                    node_id = node.get('node_id') or node.get('id') or f"node_{i}"
                    title = node.get('title') or node.get('section_title') or "Untitled"
                    summary_text = node.get('summary') or node.get('text', '')[:200]
                    
                    summary += f"\n[{node_id}] {title}\n"
                    if summary_text:
                        summary += f"  {summary_text[:200]}...\n"
        
        return summary
    
    def _parse_llm_response(self, response: str) -> List[str]:
        """Parse LLM response to extract node IDs"""
        try:
            # Try to find JSON in response
            import json
            
            # Look for JSON block
            json_start = response.find('{')
            json_end = response.rfind('}')
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end+1]
                data = json.loads(json_str)
                
                if "node_ids" in data:
                    return data["node_ids"]
                elif "nodes" in data:
                    return data["nodes"]
        
        except json.JSONDecodeError:
            pass
        
        # Fallback: extract any patterns that look like node IDs
        import re
        node_ids = re.findall(r'(node_\d+|section_\d+|[\w\-]+_\d+)', response, re.IGNORECASE)
        return list(set(node_ids)) if node_ids else ["node_0"]
    
    def _extract_node_content(self, tree_data: Dict[str, Any], node_ids: List[str]) -> List[Dict[str, str]]:
        """Extract content from specific nodes"""
        extracted = []
        
        if not isinstance(tree_data, list):
            tree_data = [tree_data]
        
        for node in tree_data:
            if isinstance(node, dict):
                node_id = node.get('node_id') or node.get('id')
                
                # Check if this node matches any of the requested IDs
                for requested_id in node_ids:
                    if requested_id in str(node_id):
                        extracted.append({
                            'id': node_id,
                            'title': node.get('title') or node.get('section_title'),
                            'text': node.get('text') or node.get('content') or node.get('summary', '')[:1000]
                        })
                        break
        
        return extracted
    
    def _get_sample_node(self, tree_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get sample node from tree for inspection"""
        if isinstance(tree_data, list) and len(tree_data) > 0:
            node = tree_data[0]
            if isinstance(node, dict):
                return {
                    "keys": list(node.keys()),
                    "id": node.get('node_id') or node.get('id'),
                    "title": node.get('title')[:50] if node.get('title') else None,
                    "has_text": 'text' in node or 'content' in node
                }
        
        return {"type": "unknown"}
    
    def _print_summary(self):
        """Print test summary"""
        total_time = self.results.get("total_duration_seconds", 0)
        
        logger.info("\n" + "="*80)
        logger.info("E2E TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"PDF: {self.results['pdf_file']}")
        logger.info(f"Model: {self.results['model_used']}")
        logger.info(f"Status: {self.results['status']}")
        logger.info(f"Total Duration: {total_time:.2f} seconds")
        
        logger.info("\nStep Durations:")
        for step_name, step_data in self.results["steps"].items():
            duration = step_data.get("duration_seconds", 0)
            logger.info(f"  {step_name}: {duration:.2f}s")
        
        logger.info("\n" + "="*80)


def main():
    """Main entry point"""
    pdf_path = "/workspace/PageIndexOllama/tests/pdfs/attention_is_all_you_need.pdf"
    
    logger.info("╔" + "="*78 + "╗")
    logger.info("║" + " "*78 + "║")
    logger.info("║" + "PageIndex E2E Test - Full Workflow".center(78) + "║")
    logger.info("║" + " "*78 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    # Run E2E test
    runner = E2ETestRunner(pdf_path, model="mistral:7b")
    results = runner.run()
    
    # Save results to JSON
    output_path = Path("/workspace/PageIndexOllama/tests/reports/e2e_test_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n✓ Results saved to: {output_path}")
    
    return 0 if results["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
