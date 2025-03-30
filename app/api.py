from fastapi import APIRouter, HTTPException
import json
import os

from app.tasks import scrape_all, scrape_amazon_offers, scrape_magalu_offers

router = APIRouter()
DATA_DIR = "data"

def read_json_file(filename: str):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]
            return data
    except json.JSONDecodeError:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = []
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data.append(json.loads(line))
                        except:
                            pass
                return data
        except Exception as e:
            print(f"Erro ao ler arquivo linha por linha: {str(e)}")
            return []
    except Exception as e:
        print(f"Erro ao ler arquivo {filename}: {str(e)}")
        return []

@router.get("/offers/magalu")
def get_magalu_offers():
    data = read_json_file("magalu_offers.json")
    return {"count": len(data), "offers": data}

@router.get("/offers/amazon")
def get_amazon_offers():
    data = read_json_file("amazon_offers.json")
    return {"count": len(data), "offers": data}

@router.get("/offers")
def get_all_offers():
    magalu_data = read_json_file("magalu_offers.json")
    amazon_data = read_json_file("amazon_offers.json")
    all_data = magalu_data + amazon_data
    return {"count": len(all_data), "offers": all_data}

@router.post("/scrape")
async def trigger_scraping():
    """Inicia o scraping de todas as ofertas"""
    task = scrape_all.delay()
    return {"message": "Scraping iniciado", "task_id": str(task.id)}

@router.post("/scrape/magalu")
async def trigger_magalu_scraping():
    """Inicia o scraping apenas da Magazine Luiza"""
    task = scrape_magalu_offers.delay()
    return {"message": "Scraping Magalu iniciado", "task_id": str(task.id)}

@router.post("/scrape/amazon")
async def trigger_amazon_scraping():
    """Inicia o scraping apenas da Amazon"""
    task = scrape_amazon_offers.delay()
    return {"message": "Scraping Amazon iniciado", "task_id": str(task.id)}