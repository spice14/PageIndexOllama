"""Tests for model configuration (TARGET 1.4)"""

import pytest
import os
from pageindex.model_capabilities import (
    ModelCapabilities,
    get_model_capabilities,
    list_models_by_provider,
    get_recommended_model,
    validate_model_for_task,
    MODEL_REGISTRY
)
from pageindex.utils import (
    get_effective_ollama_model,
    get_model_for_provider,
    validate_model_config,
    ConfigLoader
)


class TestModelCapabilities:
    """Test model capabilities registry"""
    
    def test_phi3_3_8b_capabilities(self):
        """Test phi3:3.8b (default 3B model) capabilities"""
        caps = get_model_capabilities("phi3:3.8b")
        
        assert caps.name == "phi3:3.8b"
        assert caps.provider == "ollama"
        assert caps.parameter_count == "3.8B"
        assert caps.context_window == 4096
        assert not caps.supports_json_mode
        assert caps.supports_streaming
    
    def test_all_registered_models_have_required_fields(self):
        """All models should have required capability fields"""
        required_fields = [
            'name', 'provider', 'context_window',
            'supports_json_mode', 'supports_streaming'
        ]
        
        for model_name, caps in MODEL_REGISTRY.items():
            for field in required_fields:
                assert hasattr(caps, field), f"{model_name} missing {field}"
    
    def test_openai_models_in_registry(self):
        """OpenAI models should be in registry"""
        assert "gpt-4o-2024-11-20" in MODEL_REGISTRY
        assert "gpt-3.5-turbo" in MODEL_REGISTRY
        
        gpt4_caps = get_model_capabilities("gpt-4o-2024-11-20")
        assert gpt4_caps.provider == "openai"
        assert gpt4_caps.context_window == 128000
    
    def test_ollama_3b_models_in_registry(self):
        """3B Ollama models should be in registry"""
        assert "phi3:3.8b" in MODEL_REGISTRY
        assert "gemma:3b" in MODEL_REGISTRY
        
        phi3_caps = get_model_capabilities("phi3:3.8b")
        assert phi3_caps.provider == "ollama"
        assert "3" in phi3_caps.parameter_count or "3.8" in phi3_caps.parameter_count
    
    def test_validate_prompt_tokens(self):
        """Test token validation for context window"""
        caps = get_model_capabilities("phi3:3.8b")
        
        # Should accept prompts that fit
        assert caps.validate_prompt_tokens(2000)
        
        # Should reject prompts that are too large
        assert not caps.validate_prompt_tokens(5000)
    
    def test_get_safe_chunk_size(self):
        """Test safe chunk size calculation"""
        caps = get_model_capabilities("phi3:3.8b")
        chunk_size = caps.get_safe_chunk_size()
        
        assert chunk_size > 0
        assert chunk_size < caps.context_window * 4  # Sanity check
    
    def test_unknown_model_fallback(self):
        """Unknown models should return fallback capabilities"""
        caps = get_model_capabilities("unknown-model")
        
        assert caps.name == "unknown-model"
        assert caps.provider == "unknown"
        assert caps.context_window > 0


class TestModelSelection:
    """Test model selection logic"""
    
    def test_list_models_by_provider_openai(self):
        """Should list OpenAI models"""
        openai_models = list_models_by_provider("openai")
        assert len(openai_models) > 0
        assert "gpt-4o-2024-11-20" in openai_models
    
    def test_list_models_by_provider_ollama(self):
        """Should list Ollama models"""
        ollama_models = list_models_by_provider("ollama")
        assert len(ollama_models) > 0
        assert "phi3:3.8b" in ollama_models
        assert "mistral:7b" in ollama_models
    
    def test_get_recommended_model_openai(self):
        """Should recommend appropriate OpenAI model"""
        model = get_recommended_model("openai")
        assert model == "gpt-4o-2024-11-20"
    
    def test_get_recommended_model_ollama_default(self):
        """Should recommend phi3:3.8b as default Ollama model"""
        model = get_recommended_model("ollama")
        assert model == "phi3:3.8b"
    
    def test_get_recommended_model_ollama_with_limit(self):
        """Should respect parameter limit"""
        # Should get 3B model or smaller
        model = get_recommended_model("ollama", parameter_limit=4)
        caps = get_model_capabilities(model)
        
        # Parse parameter count
        param_str = caps.parameter_count.rstrip("B")
        if param_str != "unknown":
            param_count = float(param_str)
            assert param_count <= 4
    
    def test_validate_model_for_task(self):
        """Test model validation for tasks"""
        # phi3:3.8b should handle 2K token tasks
        assert validate_model_for_task("phi3:3.8b", 2000)
        
        # Should reject tasks that exceed context window
        assert not validate_model_for_task("phi3:3.8b", 10000)


class TestConfigYamlUpdates:
    """Test config.yaml updates for TARGET 1.4"""
    
    def test_config_has_provider(self):
        """Config should have provider setting"""
        loader = ConfigLoader()
        config = loader.load()
        
        assert hasattr(config, 'provider')
        assert config.provider in ['openai', 'ollama', 'hybrid']
    
    def test_config_has_ollama_model(self):
        """Config should have ollama_model setting with 3B default"""
        loader = ConfigLoader()
        config = loader.load()
        
        assert hasattr(config, 'ollama_model')
        assert isinstance(config.ollama_model, str)
        
        # Should be phi3:3.8b (3B model)
        assert "phi3" in config.ollama_model.lower() or "3" in config.ollama_model
    
    def test_config_has_model_config(self):
        """Config should have model_config section"""
        loader = ConfigLoader()
        config = loader.load()
        
        assert hasattr(config, 'model_config')
    
    def test_config_openai_model_preserved(self):
        """Config should preserve OpenAI model for backward compatibility"""
        loader = ConfigLoader()
        config = loader.load()
        
        assert hasattr(config, 'model')
        assert isinstance(config.model, str)
        assert "gpt" in config.model.lower()


class TestUtilsFunctions:
    """Test utils.py model selection functions"""
    
    def test_get_effective_ollama_model_default(self):
        """Should return phi3:3.8b as default"""
        # Clear environment
        if "OLLAMA_MODEL" in os.environ:
            original = os.environ["OLLAMA_MODEL"]
            del os.environ["OLLAMA_MODEL"]
        else:
            original = None
        
        model = get_effective_ollama_model()
        assert "phi3" in model.lower() or "3" in model
        
        # Restore
        if original:
            os.environ["OLLAMA_MODEL"] = original
    
    def test_get_effective_ollama_model_from_config(self):
        """Should use config model if no env var"""
        # Save and clear environment
        if "OLLAMA_MODEL" in os.environ:
            original = os.environ["OLLAMA_MODEL"]
            del os.environ["OLLAMA_MODEL"]
        else:
            original = None
        
        # Need to reload module to clear cached value
        from pageindex import utils
        import importlib
        importlib.reload(utils)
        
        model = utils.get_effective_ollama_model(config_model="mistral:7b")
        assert model == "mistral:7b"
        
        # Restore
        if original:
            os.environ["OLLAMA_MODEL"] = original
            importlib.reload(utils)
    
    def test_get_model_for_provider_openai(self):
        """Should get OpenAI model"""
        loader = ConfigLoader()
        config = loader.load()
        
        model = get_model_for_provider("openai", config)
        assert "gpt" in model.lower()
    
    def test_get_model_for_provider_ollama(self):
        """Should get Ollama model"""
        loader = ConfigLoader()
        config = loader.load()
        
        model = get_model_for_provider("ollama", config)
        assert isinstance(model, str)
        assert len(model) > 0
    
    def test_validate_model_config_valid(self):
        """Should validate matching model/provider"""
        assert validate_model_config("phi3:3.8b", "ollama")
        assert validate_model_config("gpt-4o-2024-11-20", "openai")
    
    def test_validate_model_config_invalid(self):
        """Should detect mismatched model/provider"""
        # OpenAI model with Ollama provider should not match
        result = validate_model_config("gpt-4o-2024-11-20", "ollama")
        assert not result
    
    def test_validate_model_config_unknown_model(self):
        """Should allow unknown models through (permissive)"""
        # Unknown models return True (permissive) because they might be custom models
        # The function logs a warning but doesn't block them
        result = validate_model_config("unknown-model-123", "unknown")
        # For unknown models with unknown provider, should be permissive
        assert result is not False


class Test3BModelDefault:
    """Test that 3B model is properly configured as default"""
    
    def test_default_model_is_3b(self):
        """Verify default model is approximately 3B parameters"""
        loader = ConfigLoader()
        config = loader.load()
        
        model = config.ollama_model
        caps = get_model_capabilities(model)
        
        # Should be 3B or close to it
        param_str = caps.parameter_count.rstrip("B")
        if param_str != "unknown":
            param_count = float(param_str)
            assert 2.5 <= param_count <= 4.5, \
                f"Default model {model} has {param_count}B params, expected ~3B"
    
    def test_default_model_has_reasonable_context(self):
        """Default 3B model should have reasonable context window"""
        loader = ConfigLoader()
        config = loader.load()
        
        model = config.ollama_model
        caps = get_model_capabilities(model)
        
        # Should have at least 4K context
        assert caps.context_window >= 4096
    
    def test_default_model_supports_streaming(self):
        """Default model should support streaming"""
        loader = ConfigLoader()
        config = loader.load()
        
        model = config.ollama_model
        caps = get_model_capabilities(model)
        
        assert caps.supports_streaming


class TestBackwardCompatibility:
    """Ensure TARGET 1.4 maintains backward compatibility"""
    
    def test_openai_model_still_accessible(self):
        """OpenAI model should still be accessible from config"""
        loader = ConfigLoader()
        config = loader.load()
        
        assert hasattr(config, 'model')
        assert isinstance(config.model, str)
    
    def test_config_loader_still_works(self):
        """ConfigLoader should still work without errors"""
        loader = ConfigLoader()
        config = loader.load()
        
        assert config is not None
        assert hasattr(config, 'model')
        assert hasattr(config, 'provider')
    
    def test_existing_config_attributes_preserved(self):
        """Existing config attributes should be preserved"""
        loader = ConfigLoader()
        config = loader.load()
        
        # Original attributes
        assert hasattr(config, 'toc_check_page_num')
        assert hasattr(config, 'max_page_num_each_node')
        assert hasattr(config, 'max_token_num_each_node')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
