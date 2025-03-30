from typing import Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
import random
from datetime import datetime
import logging
from requests.exceptions import RequestException

class BaseScraper:
    def __init__(self):
        self.session = requests.Session()
        self.timeout = 30

    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers randomizados para as requisições"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        ]
        return {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def fetch_page(self, url: str) -> str:
        """Faz a requisição HTTP com tratamento de erros"""
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.text  
        except RequestException as e:
            logging.error(f"Erro ao fazer requisição para {url}: {e}")
            return ""

    def parse_html(self, html_content: str) -> BeautifulSoup:
        """Parse do HTML com tratamento de erros"""
        if not html_content:
            return BeautifulSoup("", "lxml") 
        try:
            return BeautifulSoup(html_content, "lxml")
        except Exception as e:
            logging.error(f"Erro ao fazer parse do HTML: {e}")
            return BeautifulSoup("", "lxml")