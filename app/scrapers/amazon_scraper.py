from app.scrapers.base_scraper import BaseScraper
from datetime import datetime
import logging
import json
from pathlib import Path
import random
import time

class AmazonScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.urls = [
            "https://www.amazon.com.br/deals?ref_=nav_cs_gb",
            "https://www.amazon.com.br/gp/goldbox",
            "https://www.amazon.com.br/s?k=ofertas+do+dia"
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_offers(self):
        offers = []

        for url in self.urls:
            try:
                self.logger.info(f"Tentando scraping da Amazon: {url}")
                html_content = self.fetch_page(url)

                # salvar o html pra debugar
                debug_path = Path("debug")
                debug_path.mkdir(exist_ok=True)
                with open(debug_path / f"amazon_debug_{url.split('/')[-1]}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)

                soup = self.parse_html(html_content)

                selectors = [
                    {"type": "div", "attrs": {"data-testid": "deal-card"}},
                    {"type": "div", "attrs": {"data-component-type": "s-search-result"}},
                    {"type": "div", "attrs": {"class": "DealGridItem-module__dealItem"}},
                    {"type": "div", "attrs": {"class": "a-section a-spacing-base"}},
                    {"type": "div", "attrs": {"class": "sg-col-4-of-24 sg-col-4-of-12 sg-col-4-of-36 s-result-item"}}
                ]

                products = []
                for selector in selectors:
                    if "class" in selector["attrs"]:
                        products = soup.find_all(selector["type"],
                                               class_=lambda c: c and selector["attrs"]["class"] in c)
                    else:
                        products = soup.find_all(selector["type"], selector["attrs"])

                    if products:
                        self.logger.info(f"Encontrados {len(products)} produtos com o seletor {selector}")
                        break

                if not products:
                    price_elements = soup.select("span.a-price")
                    for price in price_elements:
                        product_container = price.find_parent("div", class_=lambda c: c and "a-section" in c)
                        if product_container:
                            products.append(product_container)

                    self.logger.info(f"Encontrados {len(products)} produtos com abordagem alternativa")

                for product in products:
                    try:
                        name = None
                        name_selectors = [
                            product.select_one("span.a-size-base-plus"),
                            product.select_one("span.a-size-medium"),
                            product.select_one("a.a-link-normal span"),
                            product.select_one("h2 a span"),
                            product.select_one("h2")
                        ]

                        for selector in name_selectors:
                            if selector and selector.get_text(strip=True):
                                name = selector.get_text(strip=True)
                                break

                        price_vista = None
                        price_selectors = [
                            product.select_one("span.a-price .a-offscreen"),
                            product.select_one("span.a-price-whole"),
                            product.select_one("span.a-price")
                        ]

                        for selector in price_selectors:
                            if selector:
                                price_text = selector.get_text(strip=True)
                                if price_text:
                                    price_vista = price_text
                                    break

                        price_prazo = None
                        installment_selectors = [
                            product.select_one("span.a-size-small:contains('x')"),
                            product.select_one("span:contains('em até')")
                        ]

                        for selector in installment_selectors:
                            if selector and selector.get_text(strip=True):
                                price_prazo = selector.get_text(strip=True)
                                break

                        disponivel = True
                        unavailable_selectors = [
                            product.select_one("span.a-color-price.unavailablePrice"),
                            product.select_one("span.a-color-error"),
                            product.select_one("span:contains('Indisponível')")
                        ]

                        for selector in unavailable_selectors:
                            if selector:
                                disponivel = False
                                break

                        link = None
                        link_elem = product.select_one("a[href]")
                        if link_elem:
                            href = link_elem["href"]
                            link = f"https://www.amazon.com.br{href}" if not href.startswith('http') else href

                        if name and price_vista:
                            offer = {
                                "nome": name,
                                "preco_vista": price_vista,
                                "preco_prazo": price_prazo,
                                "disponivel": disponivel,
                                "url": link or url,
                                "timestamp": datetime.now().isoformat()
                            }
                            offers.append(offer)
                            self.logger.info(f"Oferta encontrada: {name}")

                    except Exception as e:
                        self.logger.error(f"Erro ao processar produto: {str(e)}")
                        continue

                if offers:
                    break

                time.sleep(random.uniform(1, 3))

            except Exception as e:
                self.logger.error(f"Erro durante o scraping da Amazon: {str(e)}")

        self.logger.info(f"Total de ofertas encontradas na Amazon: {len(offers)}")

        if offers:
            debug_path = Path("debug")
            debug_path.mkdir(exist_ok=True)
            with open(debug_path / "amazon_offers_debug.json", "w", encoding="utf-8") as f:
                json.dump(offers, f, ensure_ascii=False, indent=2)

        return offers

    def fetch_page(self, url):
        """
        Sobrescreve o método fetch_page do BaseScraper para incluir headers específicos
        """
        try:
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
            ]

            headers = self.headers.copy()
            headers["User-Agent"] = random.choice(user_agents)

            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Erro ao fazer requisição para {url}: {str(e)}")
            return ""