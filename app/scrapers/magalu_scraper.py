from app.scrapers.base_scraper import BaseScraper
from datetime import datetime
import logging
import json
from pathlib import Path
import random
import time
import re
import requests

class MagaluScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.api_url = "https://www.magazineluiza.com.br/busca/smartphone/?page=1&sortby=price_asc"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.magazineluiza.com.br/",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0"
        }
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_offers(self):
        offers = []
        try:
            self.logger.info(f"Tentando scraping da Magazine Luiza: {self.api_url}")

            response = requests.get(self.api_url, headers=self.headers)
            html_content = response.text

            debug_path = Path("debug")
            debug_path.mkdir(exist_ok=True)
            with open(debug_path / "magalu_debug.html", "w", encoding="utf-8") as f:
                f.write(html_content)

            json_data = self.extract_json_from_html(html_content)

            if json_data:
                self.logger.info("Dados JSON encontrados no HTML")

                products = self.extract_products_from_json(json_data)

                if products:
                    self.logger.info(f"Extraídos {len(products)} produtos do JSON")
                    offers = products

            if not offers:
                self.logger.info("Tentando método tradicional de scraping")
                soup = self.parse_html(html_content)

                product_cards = soup.select("[data-testid='product-card']") or soup.select(".productCard")

                self.logger.info(f"Encontrados {len(product_cards)} cards de produtos")

                for card in product_cards:
                    try:
                        name_elem = card.select_one("[data-testid='product-title']") or card.select_one("h2")
                        name = name_elem.get_text(strip=True) if name_elem else None

                        price_elem = card.select_one("[data-testid='price-value']") or card.select_one(".price-template__text")
                        price_vista = price_elem.get_text(strip=True) if price_elem else None

                        installment_elem = card.select_one("[data-testid='installment']") or card.select_one(".price-installments")
                        price_prazo = installment_elem.get_text(strip=True) if installment_elem else None

                        link_elem = card.select_one("a[href]")
                        link = link_elem["href"] if link_elem else None
                        if link and not link.startswith("http"):
                            link = f"https://www.magazineluiza.com.br{link}"

                        unavailable_elem = card.select_one(".unavailableProduct") or card.select_one("[data-testid='unavailable']")
                        disponivel = not bool(unavailable_elem)

                        if name and price_vista:
                            offer = {
                                "nome": name,
                                "preco_vista": price_vista,
                                "preco_prazo": price_prazo,
                                "disponivel": disponivel,
                                "url": link or self.api_url,
                                "timestamp": datetime.now().isoformat()
                            }
                            offers.append(offer)
                            self.logger.info(f"Oferta encontrada: {name}")
                    except Exception as e:
                        self.logger.error(f"Erro ao processar card de produto: {str(e)}")

            self.logger.info(f"Total de ofertas encontradas na Magazine Luiza: {len(offers)}")

            if offers:
                with open(debug_path / "magalu_offers_debug.json", "w", encoding="utf-8") as f:
                    json.dump(offers, f, ensure_ascii=False, indent=4)

        except Exception as e:
            self.logger.error(f"Erro durante o scraping da Magazine Luiza: {str(e)}")

        return offers

    def extract_json_from_html(self, html_content):
        """Extrai dados JSON embutidos no HTML"""
        try:
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});\s*</script>',
                r'window\.__PRELOADED_STATE__\s*=\s*({.*?});\s*</script>',
                r'window\.__APOLLO_STATE__\s*=\s*({.*?});\s*</script>',
                r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, html_content, re.DOTALL)
                if matches:
                    for match in matches:
                        try:
                            return json.loads(match)
                        except:
                            continue

            return None
        except Exception as e:
            self.logger.error(f"Erro ao extrair JSON do HTML: {str(e)}")
            return None

    def extract_products_from_json(self, json_data):
        """Extrai produtos de diferentes formatos de JSON"""
        products = []

        try:
            if "results" in json_data and "products" in json_data["results"]:
                raw_products = json_data["results"]["products"]
            elif "products" in json_data:
                raw_products = json_data["products"]
            elif "searchResult" in json_data and "items" in json_data["searchResult"]:
                raw_products = json_data["searchResult"]["items"]
            elif "props" in json_data and "pageProps" in json_data["props"]:
                if "products" in json_data["props"]["pageProps"]:
                    raw_products = json_data["props"]["pageProps"]["products"]
                elif "searchResult" in json_data["props"]["pageProps"]:
                    raw_products = json_data["props"]["pageProps"]["searchResult"]["products"]
                else:
                    raw_products = []
            else:
                raw_products = self.find_products_in_json(json_data)

            for product in raw_products:
                try:
                    name = self.extract_field(product, ["title", "name", "productTitle"])
                    price_vista = self.extract_field(product, ["price", "bestPrice", "priceValue", "sellingPrice"])

                    if isinstance(price_vista, (int, float)):
                        price_vista = f"R$ {price_vista:.2f}".replace(".", ",")

                    installments = self.extract_field(product, ["installment", "installments"])
                    price_prazo = None

                    if isinstance(installments, dict):
                        count = installments.get("count") or installments.get("quantity")
                        value = installments.get("value") or installments.get("amount")

                        if count and value:
                            if isinstance(value, (int, float)):
                                value = f"R$ {value:.2f}".replace(".", ",")
                            price_prazo = f"{count}x de {value}"

                    url = self.extract_field(product, ["url", "permalink", "link"])
                    if url and not url.startswith("http"):
                        url = f"https://www.magazineluiza.com.br{url}"

                    available = self.extract_field(product, ["available", "availability", "inStock"])
                    disponivel = True if available is None else bool(available)

                    if name and price_vista:
                        offer = {
                            "nome": name,
                            "preco_vista": price_vista,
                            "preco_prazo": price_prazo,
                            "disponivel": disponivel,
                            "url": url or self.api_url,
                            "timestamp": datetime.now().isoformat()
                        }
                        products.append(offer)
                except Exception as e:
                    self.logger.error(f"Erro ao processar produto do JSON: {str(e)}")

        except Exception as e:
            self.logger.error(f"Erro ao extrair produtos do JSON: {str(e)}")

        return products

    def extract_field(self, obj, possible_keys):
        """Extrai um campo de um objeto usando várias chaves possíveis"""
        if not isinstance(obj, dict):
            return None

        for key in possible_keys:
            if key in obj:
                return obj[key]

        return None

    def find_products_in_json(self, json_data, max_depth=3, current_depth=0):
        """Procura recursivamente por listas que pareçam produtos no JSON"""
        if current_depth > max_depth:
            return []

        if isinstance(json_data, list) and len(json_data) > 0:
            if all(isinstance(item, dict) for item in json_data):
                product_keys = ["title", "name", "price", "url"]
                if any(any(key in item for key in product_keys) for item in json_data):
                    return json_data

        if isinstance(json_data, dict):
            for key, value in json_data.items():
                result = self.find_products_in_json(value, max_depth, current_depth + 1)
                if result:
                    return result

        return []