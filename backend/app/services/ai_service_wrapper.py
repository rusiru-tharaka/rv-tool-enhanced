"""
AI Service Wrapper for GenAI Enhancements
Extends existing Bedrock integration with prompt engineering and caching
"""

import json
import asyncio
import hashlib
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .bedrock_ai_integration import BedrockAIEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIServiceWrapper:
    """Enhanced AI service wrapper with prompt engineering and caching"""
    
    def __init__(self, profile_name: str = "smartslot", region: str = "us-east-1"):
        """Initialize AI service with existing Bedrock integration"""
        self.bedrock_engine = BedrockAIEngine(profile_name=profile_name, region=region)
        self.response_cache = {}  # Simple in-memory cache
        self.cache_ttl = timedelta(hours=1)  # Cache responses for 1 hour
        
        logger.info("✅ AI Service Wrapper initialized with enhanced capabilities")
    
    def _generate_cache_key(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate cache key for prompt"""
        content = f"{prompt}_{max_tokens}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        
        cache_time = cache_entry.get('timestamp')
        if not cache_time:
            return False
        
        return datetime.now() - cache_time < self.cache_ttl
    
    async def invoke_ai(self, prompt: str, max_tokens: int = 4000, use_cache: bool = True) -> Optional[str]:
        """
        Invoke AI with caching and error handling
        
        Args:
            prompt: The prompt to send to AI
            max_tokens: Maximum tokens in response
            use_cache: Whether to use response caching
            
        Returns:
            AI response text or None if failed
        """
        
        # Check cache first if enabled
        if use_cache:
            cache_key = self._generate_cache_key(prompt, max_tokens)
            cached_response = self.response_cache.get(cache_key)
            
            if cached_response and self._is_cache_valid(cached_response):
                logger.info("✅ Using cached AI response")
                return cached_response['response']
        
        # Invoke AI service
        try:
            logger.info("🤖 Invoking AI service...")
            response = await self.bedrock_engine.invoke_claude(prompt, max_tokens)
            
            if response and use_cache:
                # Cache the response
                cache_key = self._generate_cache_key(prompt, max_tokens)
                self.response_cache[cache_key] = {
                    'response': response,
                    'timestamp': datetime.now()
                }
                logger.info("💾 Response cached for future use")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ AI service invocation failed: {e}")
            return None
    
    def create_structured_prompt(self, 
                                system_role: str,
                                context: str,
                                task: str,
                                output_format: str,
                                examples: Optional[str] = None) -> str:
        """
        Create a structured prompt for consistent AI responses
        
        Args:
            system_role: Role definition for the AI
            context: Context information
            task: Specific task to perform
            output_format: Expected output format
            examples: Optional examples
            
        Returns:
            Formatted prompt string
        """
        
        prompt_parts = [
            f"ROLE: {system_role}",
            "",
            f"CONTEXT:\n{context}",
            "",
            f"TASK:\n{task}",
            "",
            f"OUTPUT FORMAT:\n{output_format}"
        ]
        
        if examples:
            prompt_parts.extend([
                "",
                f"EXAMPLES:\n{examples}"
            ])
        
        prompt_parts.extend([
            "",
            "Please provide your analysis following the specified format exactly."
        ])
        
        return "\n".join(prompt_parts)
    
    def validate_json_response(self, response: str) -> Optional[Dict]:
        """
        Validate and parse JSON response from AI
        
        Args:
            response: AI response string
            
        Returns:
            Parsed JSON dict or None if invalid
        """
        if not response:
            return None
        
        try:
            # Try to find JSON in the response
            response = response.strip()
            
            # Look for JSON block markers
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end].strip()
            elif response.startswith("{") and response.endswith("}"):
                # Already looks like JSON
                pass
            else:
                # Try to find JSON-like content
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end > start:
                    response = response[start:end]
            
            return json.loads(response)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response[:500]}...")
            return None
    
    def calculate_confidence_score(self, 
                                 response_data: Dict,
                                 validation_criteria: List[str]) -> float:
        """
        Calculate confidence score for AI response
        
        Args:
            response_data: Parsed AI response
            validation_criteria: List of required fields/criteria
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not response_data:
            return 0.0
        
        score = 0.0
        total_criteria = len(validation_criteria)
        
        if total_criteria == 0:
            return 1.0
        
        for criterion in validation_criteria:
            if criterion in response_data and response_data[criterion]:
                score += 1.0
        
        return score / total_criteria
    
    async def analyze_with_fallback(self,
                                  primary_prompt: str,
                                  fallback_function: callable,
                                  fallback_args: tuple = (),
                                  max_tokens: int = 4000) -> Dict[str, Any]:
        """
        Analyze with AI and fallback to traditional logic if AI fails
        
        Args:
            primary_prompt: Primary AI prompt
            fallback_function: Function to call if AI fails
            fallback_args: Arguments for fallback function
            max_tokens: Maximum tokens for AI response
            
        Returns:
            Analysis results with metadata
        """
        
        result = {
            'ai_used': False,
            'fallback_used': False,
            'confidence': 0.0,
            'data': None,
            'error': None
        }
        
        # Try AI analysis first
        try:
            ai_response = await self.invoke_ai(primary_prompt, max_tokens)
            
            if ai_response:
                parsed_response = self.validate_json_response(ai_response)
                
                if parsed_response:
                    result['ai_used'] = True
                    result['data'] = parsed_response
                    result['confidence'] = 0.8  # Base confidence for successful AI response
                    logger.info("✅ AI analysis successful")
                    return result
        
        except Exception as e:
            logger.error(f"❌ AI analysis failed: {e}")
            result['error'] = str(e)
        
        # Fallback to traditional logic
        try:
            logger.info("🔄 Falling back to traditional analysis")
            fallback_result = fallback_function(*fallback_args)
            
            result['fallback_used'] = True
            result['data'] = fallback_result
            result['confidence'] = 0.6  # Lower confidence for fallback
            logger.info("✅ Fallback analysis successful")
            
        except Exception as e:
            logger.error(f"❌ Fallback analysis also failed: {e}")
            result['error'] = f"Both AI and fallback failed: {str(e)}"
        
        return result
    
    def clear_cache(self):
        """Clear the response cache"""
        self.response_cache.clear()
        logger.info("🗑️ AI response cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        valid_entries = sum(1 for entry in self.response_cache.values() 
                          if self._is_cache_valid(entry))
        
        return {
            'total_entries': len(self.response_cache),
            'valid_entries': valid_entries,
            'cache_hit_potential': valid_entries / max(len(self.response_cache), 1)
        }
