from apify import Actor
from crawlee.crawlers import PlaywrightCrawler
from crawlee.http_clients import HttpxHttpClient
from .routes import router

async def main() -> None:
    """The crawler entry point."""
    async with Actor:
        actor_input = await Actor.get_input()
        max_items = actor_input.get('maxItems', 0)
        crawler = PlaywrightCrawler(
            request_handler=router,
            headless=False,
            max_requests_per_crawl=max_items,
            http_client=HttpxHttpClient(),
        )

        await crawler.run(
            [
                'https://nike.com/',
            ]
        )
        await crawler.export_data('shoes.csv')