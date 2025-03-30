from contextlib import contextmanager
from typing import Dict, List, Any
import os
import json
import logging
from celery import Celery

from app.scrapers.magalu_scraper import MagaluScraper
from app.scrapers.amazon_scraper import AmazonScraper

celery_app = Celery("tasks", broker="redis://redis:6379/0")

logging.basicConfig(level=logging.INFO)

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

@contextmanager
def json_file_handler(filename: str, mode: str = "a"):
    """Context manager para manipulação segura de arquivos JSON"""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, mode, encoding="utf-8") as f:
            yield f
    except Exception as e:
        logging.error(f"Erro ao manipular arquivo {filename}: {e}")
        raise

def save_offers(offers: List[Dict[str, Any]], filename: str) -> None:
    """Salva as ofertas em um arquivo JSON"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)

        filepath = os.path.join(DATA_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(offers, f, ensure_ascii=False, indent=2)

        logging.info(f"Ofertas salvas com sucesso em {filename}")
    except Exception as e:
        logging.error(f"Erro ao salvar ofertas em {filename}: {e}")
        raise

@celery_app.task
def scrape_magalu_offers():
    """Tarefa para coletar ofertas da Magazine Luiza"""
    try:
        logging.info("Iniciando scraping Magazine Luiza")
        scraper = MagaluScraper()
        offers = scraper.get_offers()

        if offers:
            save_offers(offers, "magalu_offers.json")
            logging.info(f"Scraping Magazine Luiza finalizado: {len(offers)} ofertas coletadas")
            return {"status": "success", "count": len(offers)}
        else:
            logging.warning("Nenhuma oferta encontrada na Magazine Luiza")
            return {"status": "warning", "count": 0}

    except Exception as e:
        logging.error(f"Erro no scraping Magazine Luiza: {str(e)}")
        return {"status": "error", "message": str(e)}

@celery_app.task
def scrape_amazon_offers():
    try:
        logging.info("Iniciando scraping Amazon")
        scraper = AmazonScraper()
        offers = scraper.get_offers()

        if offers:
            save_offers(offers, "amazon_offers.json")
            logging.info(f"Scraping Amazon finalizado: {len(offers)} ofertas coletadas")
            return {"status": "success", "count": len(offers)}
        else:
            logging.warning("Nenhuma oferta encontrada na Amazon")
            return {"status": "warning", "count": 0}

    except Exception as e:
        logging.error(f"Erro no scraping Amazon: {str(e)}")
        return {"status": "error", "message": str(e)}

@celery_app.task
def scrape_all():
    """
    Tarefa para executar o scraping em todos os sites
    """
    results = {
        "magalu": scrape_magalu_offers(),
        "amazon": scrape_amazon_offers()
    }
    return results