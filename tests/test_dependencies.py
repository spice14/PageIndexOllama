"""Tests for package dependencies (TARGET 1.1)"""

import pytest
import sys


class TestCoreDependencies:
    """Test that all core dependencies are available"""
    
    def test_openai_available(self):
        """OpenAI SDK should be available (for fallback)"""
        import openai
        assert hasattr(openai, 'OpenAI')
        assert hasattr(openai, 'AsyncOpenAI')
    
    def test_requests_available(self):
        """requests library should be available (for Ollama HTTP)"""
        import requests
        assert hasattr(requests, 'get')
        assert hasattr(requests, 'post')
        assert hasattr(requests, 'Session')
    
    def test_aiohttp_available(self):
        """aiohttp should be available (for async Ollama)"""
        import aiohttp
        assert hasattr(aiohttp, 'ClientSession')
    
    def test_tiktoken_available(self):
        """tiktoken should be available (for token counting)"""
        import tiktoken
        assert hasattr(tiktoken, 'encoding_for_model')
    
    def test_pyyaml_available(self):
        """PyYAML should be available (for config)"""
        import yaml
        assert hasattr(yaml, 'safe_load')
        assert hasattr(yaml, 'safe_dump')
    
    def test_pymupdf_available(self):
        """PyMuPDF should be available (for PDF parsing)"""
        import fitz
        assert hasattr(fitz, 'open')
    
    def test_pypdf2_available(self):
        """PyPDF2 should be available (for PDF operations)"""
        import PyPDF2
        assert hasattr(PyPDF2, 'PdfReader')
    
    def test_dotenv_available(self):
        """python-dotenv should be available (for .env files)"""
        from dotenv import load_dotenv
        assert callable(load_dotenv)


class TestDependencyVersions:
    """Test that dependencies meet minimum version requirements"""
    
    def test_requests_version(self):
        """requests should be >= 2.31.0"""
        import requests
        version = requests.__version__
        major, minor, _ = map(int, version.split('.')[:3])
        assert major >= 2
        if major == 2:
            assert minor >= 31
    
    def test_aiohttp_version(self):
        """aiohttp should be >= 3.9.0"""
        import aiohttp
        version = aiohttp.__version__
        major, minor = map(int, version.split('.')[:2])
        assert major >= 3
        if major == 3:
            assert minor >= 9
    
    def test_tiktoken_version(self):
        """tiktoken should be >= 0.5.0"""
        import tiktoken
        version = tiktoken.__version__
        major, minor = map(int, version.split('.')[:2])
        assert major >= 0
        if major == 0:
            assert minor >= 5
    
    def test_pyyaml_version(self):
        """PyYAML should be >= 6.0.0"""
        import yaml
        version = yaml.__version__
        major, _ = map(int, version.split('.')[:2])
        assert major >= 6


class TestDependencyIntegration:
    """Test that dependencies integrate correctly with pageindex"""
    
    def test_utils_imports_successfully(self):
        """pageindex.utils should import without errors"""
        from pageindex import utils
        assert utils is not None
    
    def test_tiktoken_integration(self):
        """tiktoken should be integrated via HAS_TIKTOKEN flag"""
        from pageindex import utils
        assert hasattr(utils, 'HAS_TIKTOKEN')
        assert utils.HAS_TIKTOKEN is True
    
    def test_requests_can_make_http_call(self):
        """requests should be able to make HTTP calls"""
        import requests
        
        # Don't actually make a call in tests, just verify the API
        session = requests.Session()
        assert hasattr(session, 'post')
        assert hasattr(session, 'get')
    
    def test_aiohttp_can_create_session(self):
        """aiohttp should be able to create client sessions"""
        import aiohttp
        
        # Just verify the class exists and is instantiable
        assert callable(aiohttp.ClientSession)
    
    def test_yaml_can_load_config(self):
        """PyYAML should be able to load config.yaml"""
        import yaml
        from pathlib import Path
        
        config_path = Path(__file__).parent.parent / 'pageindex' / 'config.yaml'
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        assert isinstance(config, dict)
        assert 'model' in config
        assert 'ollama_model' in config
        assert 'provider' in config


class TestOllamaDependencies:
    """Test that Ollama-specific dependencies are ready"""
    
    def test_ollama_http_client_ready(self):
        """requests should be ready for Ollama API calls"""
        import requests
        
        # Verify JSON handling is available
        assert callable(requests.post)
    
    def test_ollama_async_client_ready(self):
        """aiohttp should be ready for async Ollama calls"""
        import aiohttp
        
        # Verify async context manager support
        assert hasattr(aiohttp.ClientSession, '__aenter__')
        assert hasattr(aiohttp.ClientSession, '__aexit__')
    
    def test_ollama_environment_variable(self):
        """OLLAMA_MODEL should be accessible from utils"""
        from pageindex import utils
        
        assert hasattr(utils, 'OLLAMA_MODEL')
        # May be None or set, both are valid


class TestBackwardCompatibility:
    """Test that OpenAI dependencies still work"""
    
    def test_openai_sdk_still_works(self):
        """OpenAI SDK should still be functional"""
        import openai
        
        # Verify classes exist
        assert hasattr(openai, 'OpenAI')
        assert hasattr(openai, 'AsyncOpenAI')
        
        # Verify can instantiate (with test key)
        # Don't actually make API calls
        client = openai.OpenAI(api_key="test-key")
        assert client is not None
    
    def test_chatgpt_api_key_still_accessible(self):
        """CHATGPT_API_KEY constant should still exist"""
        from pageindex import utils
        
        assert hasattr(utils, 'CHATGPT_API_KEY')
        # May be None if not set, which is expected
    
    def test_existing_wrapper_functions_exist(self):
        """Original wrapper functions should still exist"""
        from pageindex import utils
        
        assert hasattr(utils, 'ChatGPT_API')
        assert hasattr(utils, 'ChatGPT_API_with_finish_reason')
        assert hasattr(utils, 'ChatGPT_API_async')
        
        assert callable(utils.ChatGPT_API)
        assert callable(utils.ChatGPT_API_with_finish_reason)
        assert callable(utils.ChatGPT_API_async)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
