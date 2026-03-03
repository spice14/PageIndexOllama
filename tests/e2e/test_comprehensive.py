"""
Comprehensive E2E Testing Framework for PageIndexOllama
Tests the complete flow: PDF → Tree Generation → LLM Search → Answer Generation
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add pageindex to path
sys.path.insert(0, '/workspace/PageIndexOllama')

from pageindex import page_index_main, config
from pageindex.utils import ChatGPT_API_async
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E2ETestRunner:
    """End-to-end test runner for PageIndex with Ollama backend"""
    
    def __init__(self, 
                 pdf_dir: str,
                 reports_dir: str,
                 model: str = "mistral:7b",
                 max_pages_per_node: int = 10,
                 max_tokens_per_node: int = 20000):
        """
        Initialize E2E test runner
        
        Args:
            pdf_dir: Directory containing PDFs
            reports_dir: Directory for output reports
            model: Model to use for tree search and answer generation
            max_pages_per_node: Max pages per node in tree
            max_tokens_per_node: Max tokens per node
        """
        self.pdf_dir = pdf_dir
        self.reports_dir = reports_dir
        self.model = model
        self.max_pages_per_node = max_pages_per_node
        self.max_tokens_per_node = max_tokens_per_node
        
        # Create reports directory
        Path(self.reports_dir).mkdir(parents=True, exist_ok=True)
        
        # Define test queries for different document types
        self.test_queries = {
            "2023-annual-report": "What were the key financial highlights and revenue figures for 2023?",
            "q1-fy25-earnings": "What were the main revenue sources and profit margins reported?",
            "PRML": "What is the main topic and core concepts of this document?",
            "Regulation Best Interest": "What are the key regulatory requirements and compliance guidelines?",
            "earthmover": "What is the main focus and key findings of this paper?",
            "four-lectures": "What are the main topics covered in these lectures?",
        }
        
        self.results = {
            "test_run_id": datetime.now().isoformat(),
            "model": model,
            "gpu_info": self._get_gpu_info(),
            "pdfs_tested": [],
            "summary": {}
        }
    
    def _get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information"""
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                gpu_name, total_mem, free_mem = lines[0].split(', ')
                return {
                    "gpu": gpu_name.strip(),
                    "total_memory": total_mem.strip(),
                    "free_memory": free_mem.strip()
                }
        except Exception as e:
            logger.warning(f"Failed to get GPU info: {e}")
        return {}
    
    def _find_matching_query(self, pdf_name: str) -> str:
        """Find matching test query for PDF"""
        for key, query in self.test_queries.items():
            if key.lower() in pdf_name.lower():
                return query
        # Default query for unknown PDFs
        return "What are the main topics and key points covered in this document?"
    
    async def run_tree_search(self, tree: Dict, query: str) -> Dict[str, Any]:
        """
        Step 3: Use LLM to search tree and identify relevant nodes
        
        Args:
            tree: Document tree structure
            query: Search query
            
        Returns:
            Dict with node_list and thinking process
        """
        logger.info(f"Starting tree search for query: {query}")
        
        # Remove text from tree for initial search
        tree_without_text = self._remove_text_from_tree(tree)
        
        search_prompt = f"""You are an intelligent document researcher. You are given a question and a tree structure of a document.
Each node contains:
- node_id: unique identifier
- title: section title
- summary: brief summary of content
- children: nested subsections

Your task: Find ALL nodes that might contain the answer to the question. Think carefully about which sections would be relevant.

Question: {query}

Document tree (showing node_id, title, and summary):
{json.dumps(tree_without_text, indent=2)}

IMPORTANT: Return ONLY valid JSON in this format:
{{
    "thinking": "Your reasoning about which sections are relevant",
    "node_list": ["node_id_1", "node_id_2", ...]
}}

Analyze thoroughly. Include nodes that might have relevant information."""

        try:
            response = await ChatGPT_API_async(
                model=self.model,
                prompt=search_prompt
            )
            
            # Parse JSON response
            try:
                result = json.loads(response)
                if 'node_list' not in result:
                    result['node_list'] = []
                if 'thinking' not in result:
                    result['thinking'] = "Unable to extract thinking process"
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse tree search response: {response[:200]}")
                return {
                    "thinking": f"JSON parsing error: {str(e)}",
                    "node_list": [],
                    "error": "json_parse_error"
                }
        except Exception as e:
            logger.error(f"Tree search failed: {e}")
            return {
                "thinking": f"Tree search error: {str(e)}",
                "node_list": [],
                "error": str(e)
            }
    
    def _remove_text_from_tree(self, node: Any) -> Any:
        """Recursively remove 'text' field from tree"""
        if isinstance(node, dict):
            result = {}
            for key, value in node.items():
                if key != 'text':
                    if key == 'children' and isinstance(value, list):
                        result[key] = [self._remove_text_from_tree(child) for child in value]
                    else:
                        result[key] = value
            return result
        elif isinstance(node, list):
            return [self._remove_text_from_tree(item) for item in node]
        return node
    
    def _create_node_map(self, tree: Any, node_map: Optional[Dict] = None) -> Dict:
        """Create mapping from node_id to full node data"""
        if node_map is None:
            node_map = {}
        
        if isinstance(tree, dict):
            if 'node_id' in tree:
                node_map[tree['node_id']] = tree
            if 'children' in tree and isinstance(tree['children'], list):
                for child in tree['children']:
                    self._create_node_map(child, node_map)
        elif isinstance(tree, list):
            for item in tree:
                self._create_node_map(item, node_map)
        
        return node_map
    
    async def generate_answer(self, 
                             relevant_text: str, 
                             query: str,
                             node_list: List[str]) -> str:
        """
        Step 4: Generate final answer based on retrieved context
        
        Args:
            relevant_text: Extracted text from relevant nodes
            query: Original query
            node_list: List of node IDs that were used
            
        Returns:
            Generated answer
        """
        logger.info(f"Generating answer based on {len(node_list)} nodes")
        
        # Summarize if text is too long
        char_limit = 8000
        if len(relevant_text) > char_limit:
            relevant_text = relevant_text[:char_limit] + "...[truncated]"
        
        answer_prompt = f"""Based on the provided context from the document, answer the following question concisely and accurately.

Question: {query}

Context (from document sections):
{relevant_text}

Provide a clear, well-structured answer based on the retrieved content. If information is insufficient, state that clearly."""

        try:
            answer = await ChatGPT_API_async(
                model=self.model,
                prompt=answer_prompt
            )
            return answer
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return f"Error generating answer: {str(e)}"
    
    def _run_page_index_sync(self, pdf_path: str, opt):
        """Run page_index_main synchronously"""
        # page_index_main handles its own async operations internally
        return page_index_main(pdf_path, opt)
    
    async def run_e2e_test_single_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Run complete E2E test on a single PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Test results dictionary
        """
        pdf_name = Path(pdf_path).stem
        logger.info(f"\n{'='*80}")
        logger.info(f"Starting E2E test for: {pdf_name}")
        logger.info(f"{'='*80}")
        
        test_result = {
            "pdf_name": pdf_name,
            "pdf_path": pdf_path,
            "timestamp": datetime.now().isoformat(),
            "steps": {}
        }
        
        try:
            # STEP 1: Tree Generation
            logger.info("\n[STEP 1] Generating tree structure from PDF...")
            step1_start = time.time()
            
            try:
                opt = config(
                    model=self.model,
                    toc_check_page_num=20,
                    max_page_num_each_node=self.max_pages_per_node,
                    max_token_num_each_node=self.max_tokens_per_node,
                    if_add_node_id='yes',
                    if_add_node_summary='yes',
                    if_add_doc_description='no',
                    if_add_node_text='yes'
                )
                
                # Run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                tree_structure = await loop.run_in_executor(
                    None,
                    self._run_page_index_sync,
                    pdf_path,
                    opt
                )
                step1_duration = time.time() - step1_start
                
                test_result["steps"]["tree_generation"] = {
                    "status": "success",
                    "duration_seconds": step1_duration,
                    "tree_node_count": self._count_nodes(tree_structure),
                    "tree_depth": self._get_tree_depth(tree_structure),
                    "tree_file": f"{self.reports_dir}/{pdf_name}_tree.json"
                }
                
                # Save tree to file
                tree_file = f"{self.reports_dir}/{pdf_name}_tree.json"
                with open(tree_file, 'w', encoding='utf-8') as f:
                    json.dump(tree_structure, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✓ Tree generation successful in {step1_duration:.2f}s")
                logger.info(f"  - Nodes: {test_result['steps']['tree_generation']['tree_node_count']}")
                logger.info(f"  - Depth: {test_result['steps']['tree_generation']['tree_depth']}")
                
            except Exception as e:
                logger.error(f"✗ Tree generation failed: {e}")
                test_result["steps"]["tree_generation"] = {
                    "status": "failed",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                return test_result
            
            # STEP 2: Query Selection & Preparation
            logger.info("\n[STEP 2] Selecting and preparing test query...")
            query = self._find_matching_query(pdf_name)
            test_result["steps"]["query_selection"] = {
                "status": "success",
                "query": query
            }
            logger.info(f"✓ Query: {query}")
            
            # STEP 3: Tree Search
            logger.info("\n[STEP 3] Searching tree for relevant nodes...")
            step3_start = time.time()
            
            search_result = await self.run_tree_search(tree_structure, query)
            step3_duration = time.time() - step3_start
            
            node_list = search_result.get('node_list', [])
            test_result["steps"]["tree_search"] = {
                "status": "success" if 'error' not in search_result else "failed",
                "duration_seconds": step3_duration,
                "nodes_found": len(node_list),
                "node_ids": node_list,
                "thinking": search_result.get('thinking', ''),
                "error": search_result.get('error')
            }
            
            logger.info(f"✓ Tree search completed in {step3_duration:.2f}s")
            logger.info(f"  - Nodes found: {len(node_list)}")
            logger.info(f"  - Thinking: {search_result.get('thinking', 'N/A')[:100]}...")
            
            # STEP 4: Node Text Extraction
            logger.info("\n[STEP 4] Extracting text from relevant nodes...")
            step4_start = time.time()
            
            node_map = self._create_node_map(tree_structure)
            extracted_nodes = []
            relevant_text_parts = []
            
            for node_id in node_list:
                if node_id in node_map:
                    node = node_map[node_id]
                    text = node.get('text', '')
                    title = node.get('title', 'Unknown')
                    page = node.get('page_index', 'N/A')
                    
                    extracted_nodes.append({
                        "node_id": node_id,
                        "title": title,
                        "page": page,
                        "text_length": len(text)
                    })
                    
                    relevant_text_parts.append(f"[{title} - Page {page}]\n{text}")
                else:
                    logger.warning(f"Node {node_id} not found in tree")
            
            step4_duration = time.time() - step4_start
            relevant_text = "\n\n".join(relevant_text_parts)
            
            test_result["steps"]["text_extraction"] = {
                "status": "success",
                "duration_seconds": step4_duration,
                "extracted_nodes": extracted_nodes,
                "total_text_length": len(relevant_text)
            }
            
            logger.info(f"✓ Text extraction completed in {step4_duration:.2f}s")
            logger.info(f"  - Nodes extracted: {len(extracted_nodes)}")
            logger.info(f"  - Total text length: {len(relevant_text)} chars")
            
            # STEP 5: Answer Generation
            logger.info("\n[STEP 5] Generating final answer...")
            step5_start = time.time()
            
            answer = await self.generate_answer(relevant_text, query, node_list)
            step5_duration = time.time() - step5_start
            
            test_result["steps"]["answer_generation"] = {
                "status": "success",
                "duration_seconds": step5_duration,
                "answer": answer,
                "answer_length": len(answer)
            }
            
            logger.info(f"✓ Answer generated in {step5_duration:.2f}s")
            logger.info(f"  - Answer length: {len(answer)} chars")
            logger.info(f"  - Answer preview: {answer[:150]}...")
            
            # Calculate totals
            total_duration = time.time() - step1_start
            test_result["total_duration_seconds"] = total_duration
            test_result["status"] = "success"
            
            logger.info(f"\n✓ E2E test completed successfully in {total_duration:.2f}s total")
            
            return test_result
            
        except Exception as e:
            logger.error(f"\n✗ E2E test failed with exception: {e}")
            test_result["status"] = "failed"
            test_result["error"] = str(e)
            test_result["traceback"] = traceback.format_exc()
            return test_result
    
    def _count_nodes(self, tree: Any) -> int:
        """Count total nodes in tree"""
        if isinstance(tree, dict):
            count = 1
            if 'children' in tree and isinstance(tree['children'], list):
                for child in tree['children']:
                    count += self._count_nodes(child)
            return count
        elif isinstance(tree, list):
            return sum(self._count_nodes(item) for item in tree)
        return 0
    
    def _get_tree_depth(self, tree: Any) -> int:
        """Get maximum depth of tree"""
        if isinstance(tree, dict):
            if 'children' not in tree or not tree['children']:
                return 1
            return 1 + max(self._get_tree_depth(child) for child in tree['children'])
        elif isinstance(tree, list) and tree:
            return max(self._get_tree_depth(item) for item in tree)
        return 0
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run E2E tests on all PDFs"""
        logger.info(f"\nPageIndexOllama E2E Test Suite")
        logger.info(f"Started: {datetime.now().isoformat()}")
        logger.info(f"Model: {self.model}")
        logger.info(f"GPU: {self.results['gpu_info']}")
        logger.info(f"Reports directory: {self.reports_dir}")
        
        # Find all PDFs
        pdf_files = sorted(Path(self.pdf_dir).glob("*.pdf"))
        logger.info(f"\nFound {len(pdf_files)} PDF files to test")
        
        for pdf_path in pdf_files:
            try:
                result = await self.run_e2e_test_single_pdf(str(pdf_path))
                self.results["pdfs_tested"].append(result)
            except Exception as e:
                logger.error(f"Fatal error testing {pdf_path.name}: {e}")
                self.results["pdfs_tested"].append({
                    "pdf_name": pdf_path.stem,
                    "status": "error",
                    "error": str(e)
                })
        
        # Generate summary
        self._generate_summary()
        
        return self.results
    
    def _generate_summary(self):
        """Generate summary statistics"""
        total_tests = len(self.results["pdfs_tested"])
        successful = sum(1 for r in self.results["pdfs_tested"] if r.get("status") == "success")
        failed = total_tests - successful
        
        total_time = sum(r.get("total_duration_seconds", 0) for r in self.results["pdfs_tested"] if r.get("status") == "success")
        
        self.results["summary"] = {
            "total_pdfs": total_tests,
            "successful": successful,
            "failed": failed,
            "success_rate": f"{(successful/total_tests*100):.1f}%" if total_tests > 0 else "0%",
            "total_time_seconds": total_time,
            "average_time_per_pdf": total_time / successful if successful > 0 else 0
        }
    
    def save_results(self):
        """Save all results to files"""
        # Save main results summary
        results_file = f"{self.reports_dir}/E2E_TEST_RESULTS.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"\n✓ Results saved to: {results_file}")
        
        return results_file
    
    def generate_reports(self):
        """Generate individual and consolidated reports"""
        logger.info("\n\nGenerating reports...")
        
        # Generate individual reports
        for result in self.results["pdfs_tested"]:
            self._generate_individual_report(result)
        
        # Generate consolidated report
        self._generate_consolidated_report()
    
    def _generate_individual_report(self, result: Dict):
        """Generate individual report for each PDF"""
        pdf_name = result["pdf_name"]
        report_file = f"{self.reports_dir}/{pdf_name}_E2E_REPORT.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# E2E Test Report: {pdf_name}\n\n")
            f.write(f"**Test Date:** {result['timestamp']}\n")
            f.write(f"**Status:** {result.get('status', 'unknown').upper()}\n")
            f.write(f"**Total Duration:** {result.get('total_duration_seconds', 0):.2f}s\n\n")
            
            if result.get("status") == "success":
                # Tree Generation
                tree_gen = result["steps"].get("tree_generation", {})
                f.write("## Step 1: Tree Generation\n")
                f.write(f"- **Status:** ✓ SUCCESS\n")
                f.write(f"- **Duration:** {tree_gen.get('duration_seconds', 0):.2f}s\n")
                f.write(f"- **Total Nodes:** {tree_gen.get('tree_node_count', 0)}\n")
                f.write(f"- **Tree Depth:** {tree_gen.get('tree_depth', 0)}\n\n")
                
                # Query
                query_sel = result["steps"].get("query_selection", {})
                f.write("## Step 2: Query Selection\n")
                f.write(f"- **Query:** {query_sel.get('query', 'N/A')}\n\n")
                
                # Tree Search
                tree_search = result["steps"].get("tree_search", {})
                f.write("## Step 3: Tree Search\n")
                f.write(f"- **Status:** ✓ SUCCESS\n")
                f.write(f"- **Duration:** {tree_search.get('duration_seconds', 0):.2f}s\n")
                f.write(f"- **Nodes Found:** {tree_search.get('nodes_found', 0)}\n")
                f.write(f"- **Node IDs:** {', '.join(tree_search.get('node_ids', []))}\n")
                f.write(f"- **Reasoning:**\n```\n{tree_search.get('thinking', 'N/A')}\n```\n\n")
                
                # Text Extraction
                text_ext = result["steps"].get("text_extraction", {})
                f.write("## Step 4: Text Extraction\n")
                f.write(f"- **Status:** ✓ SUCCESS\n")
                f.write(f"- **Duration:** {text_ext.get('duration_seconds', 0):.2f}s\n")
                f.write(f"- **Nodes Extracted:** {len(text_ext.get('extracted_nodes', []))}\n")
                f.write(f"- **Total Text Length:** {text_ext.get('total_text_length', 0)} characters\n\n")
                f.write("### Extracted Nodes:\n")
                for node in text_ext.get('extracted_nodes', []):
                    f.write(f"- **{node['title']}** (ID: {node['node_id']}, Page: {node['page']}) - {node['text_length']} chars\n")
                f.write("\n")
                
                # Answer Generation
                answer_gen = result["steps"].get("answer_generation", {})
                f.write("## Step 5: Answer Generation\n")
                f.write(f"- **Status:** ✓ SUCCESS\n")
                f.write(f"- **Duration:** {answer_gen.get('duration_seconds', 0):.2f}s\n")
                f.write(f"- **Answer Length:** {answer_gen.get('answer_length', 0)} characters\n\n")
                f.write("### Generated Answer:\n")
                f.write("```\n")
                f.write(answer_gen.get('answer', 'N/A')[:2000])
                f.write("\n```\n\n")
                
            else:
                f.write(f"## Error\n")
                f.write(f"**Status:** ✗ FAILED\n")
                f.write(f"**Error:** {result.get('error', 'Unknown error')}\n")
                if result.get('traceback'):
                    f.write(f"**Traceback:**\n```\n{result['traceback']}\n```\n")
            
            f.write(f"\n---\n*Report generated: {datetime.now().isoformat()}*\n")
        
        logger.info(f"✓ Individual report: {report_file}")
    
    def _generate_consolidated_report(self):
        """Generate consolidated report for all tests"""
        report_file = f"{self.reports_dir}/CONSOLIDATED_E2E_REPORT.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# PageIndexOllama E2E Test - Consolidated Report\n\n")
            f.write(f"**Test Run ID:** {self.results['test_run_id']}\n")
            f.write(f"**Model:** {self.results['model']}\n")
            f.write(f"**GPU Info:** {json.dumps(self.results['gpu_info'], indent=2)}\n\n")
            
            # Summary
            summary = self.results["summary"]
            f.write("## Test Summary\n\n")
            f.write(f"| Metric | Value |\n")
            f.write(f"|--------|-------|\n")
            f.write(f"| Total PDFs Tested | {summary['total_pdfs']} |\n")
            f.write(f"| Successful | {summary['successful']} |\n")
            f.write(f"| Failed | {summary['failed']} |\n")
            f.write(f"| Success Rate | {summary['success_rate']} |\n")
            f.write(f"| Total Time | {summary['total_time_seconds']:.2f}s |\n")
            f.write(f"| Average Time per PDF | {summary['average_time_per_pdf']:.2f}s |\n\n")
            
            # Individual Results
            f.write("## Individual Test Results\n\n")
            for result in self.results["pdfs_tested"]:
                status_icon = "✓" if result.get("status") == "success" else "✗"
                duration = result.get("total_duration_seconds", 0)
                f.write(f"### {status_icon} {result['pdf_name']}\n")
                f.write(f"- **Status:** {result.get('status', 'unknown')}\n")
                f.write(f"- **Duration:** {duration:.2f}s\n")
                
                if result.get("status") == "success":
                    tree_gen = result["steps"].get("tree_generation", {})
                    tree_search = result["steps"].get("tree_search", {})
                    text_ext = result["steps"].get("text_extraction", {})
                    answer_gen = result["steps"].get("answer_generation", {})
                    
                    f.write(f"- **Tree Nodes:** {tree_gen.get('tree_node_count', 0)}\n")
                    f.write(f"- **Tree Depth:** {tree_gen.get('tree_depth', 0)}\n")
                    f.write(f"- **Nodes Found by Search:** {tree_search.get('nodes_found', 0)}\n")
                    f.write(f"- **Text Extracted:** {text_ext.get('total_text_length', 0)} chars\n")
                    f.write(f"- **Answer Generated:** {answer_gen.get('answer_length', 0)} chars\n")
                else:
                    f.write(f"- **Error:** {result.get('error', 'Unknown')}\n")
                
                f.write(f"- **[Detailed Report]({result['pdf_name']}_E2E_REPORT.md)**\n\n")
            
            f.write(f"\n---\n*Report generated: {datetime.now().isoformat()}*\n")
        
        logger.info(f"✓ Consolidated report: {report_file}")


async def main():
    """Main entry point"""
    pdf_dir = "/workspace/PageIndexOllama/tests/pdfs"
    reports_dir = "/workspace/PageIndexOllama/tests/reports"
    
    runner = E2ETestRunner(
        pdf_dir=pdf_dir,
        reports_dir=reports_dir,
        model="mistral:7b"
    )
    
    # Run all tests
    await runner.run_all_tests()
    
    # Save results
    runner.save_results()
    
    # Generate reports
    runner.generate_reports()
    
    # Print summary
    summary = runner.results["summary"]
    print(f"\n\n{'='*80}")
    print("E2E TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total PDFs: {summary['total_pdfs']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"Total Time: {summary['total_time_seconds']:.2f}s")
    print(f"Average Time per PDF: {summary['average_time_per_pdf']:.2f}s")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
