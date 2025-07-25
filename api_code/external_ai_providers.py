import os
import json
import boto3
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SSM client
ssm = boto3.client('ssm')

class ExternalAIProvider:
    """Base class for external AI providers"""
    
    def __init__(self):
        self.api_key = None
        self.load_api_key()
    
    def load_api_key(self):
        """Load API key from SSM Parameter Store"""
        raise NotImplementedError
    
    def generate_summary(self, text: str, summary_type: str, max_tokens: int, temperature: float) -> Tuple[str, Dict]:
        """Generate summary using the provider's API"""
        raise NotImplementedError

class OpenAIProvider(ExternalAIProvider):
    """OpenAI/GPT provider implementation"""
    
    def load_api_key(self):
        """Load OpenAI API key from SSM"""
        try:
            response = ssm.get_parameter(Name='/redact/api-keys/openai-api-key', WithDecryption=True)
            self.api_key = response['Parameter']['Value']
            if self.api_key == 'placeholder-will-be-updated-manually':
                raise ValueError("OpenAI API key not configured")
        except Exception as e:
            logger.error(f"Error loading OpenAI API key: {str(e)}")
            raise
    
    def generate_summary(self, text: str, summary_type: str, max_tokens: int, temperature: float, model: str = "gpt-4o-mini") -> Tuple[str, Dict]:
        """Generate summary using OpenAI API"""
        try:
            # Map summary types to instructions
            instructions = {
                'brief': 'Provide a 2-3 sentence summary of this document.',
                'standard': 'Provide a comprehensive summary of this document.',
                'detailed': 'Provide a detailed, in-depth summary of this document including key points, context, and implications.'
            }
            
            instruction = instructions.get(summary_type, instructions['standard'])
            
            # Prepare the API request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # OpenAI API payload
            payload = {
                'model': model,
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant that provides clear, well-structured document summaries.'
                    },
                    {
                        'role': 'user',
                        'content': f"{instruction}\n\nDocument content:\n{text[:10000]}\n\nPlease provide a clear, well-structured summary."
                    }
                ],
                'max_tokens': max_tokens,
                'temperature': temperature
            }
            
            # Make the API request
            import requests
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            result = response.json()
            summary = result['choices'][0]['message']['content'].strip()
            
            # Create metadata
            metadata = {
                'model': model,
                'provider': 'openai',
                'usage': result.get('usage', {}),
                'model_version': result.get('model', model)
            }
            
            return summary, metadata
            
        except Exception as e:
            logger.error(f"Error generating OpenAI summary: {str(e)}")
            raise

class GeminiProvider(ExternalAIProvider):
    """Google Gemini provider implementation"""
    
    def load_api_key(self):
        """Load Gemini API key from SSM"""
        try:
            response = ssm.get_parameter(Name='/redact/api-keys/gemini-api-key', WithDecryption=True)
            self.api_key = response['Parameter']['Value']
            if self.api_key == 'placeholder-will-be-updated-manually':
                raise ValueError("Gemini API key not configured")
        except Exception as e:
            logger.error(f"Error loading Gemini API key: {str(e)}")
            raise
    
    def generate_summary(self, text: str, summary_type: str, max_tokens: int, temperature: float, model: str = "gemini-1.5-flash") -> Tuple[str, Dict]:
        """Generate summary using Google Gemini API"""
        try:
            # Map summary types to instructions
            instructions = {
                'brief': 'Provide a 2-3 sentence summary of this document.',
                'standard': 'Provide a comprehensive summary of this document.',
                'detailed': 'Provide a detailed, in-depth summary of this document including key points, context, and implications.'
            }
            
            instruction = instructions.get(summary_type, instructions['standard'])
            
            # Prepare the API request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            
            # Gemini API payload
            payload = {
                'contents': [{
                    'parts': [{
                        'text': f"{instruction}\n\nDocument content:\n{text[:10000]}\n\nPlease provide a clear, well-structured summary."
                    }]
                }],
                'generationConfig': {
                    'temperature': temperature,
                    'maxOutputTokens': max_tokens
                }
            }
            
            # Make the API request
            import requests
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Extract the generated text
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    summary = candidate['content']['parts'][0]['text'].strip()
                else:
                    raise Exception("Unexpected Gemini response format")
            else:
                raise Exception("No candidates returned from Gemini API")
            
            # Create metadata
            metadata = {
                'model': model,
                'provider': 'gemini',
                'usage': result.get('usageMetadata', {}),
                'safety_ratings': candidate.get('safetyRatings', [])
            }
            
            return summary, metadata
            
        except Exception as e:
            logger.error(f"Error generating Gemini summary: {str(e)}")
            raise

# Factory function to get the appropriate provider
def get_external_ai_provider(provider_type: str) -> Optional[ExternalAIProvider]:
    """Get an instance of the specified AI provider"""
    providers = {
        'openai': OpenAIProvider,
        'gemini': GeminiProvider
    }
    
    provider_class = providers.get(provider_type)
    if provider_class:
        try:
            return provider_class()
        except Exception as e:
            logger.error(f"Failed to initialize {provider_type} provider: {str(e)}")
            return None
    
    return None