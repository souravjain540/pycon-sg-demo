# pycon-sg-demo 🇸🇬
PyCon Singapore Crawlee Demo

Target website: https://www.nike.com/

Goal: To scrape all the shoes from all the categories and store details like URL, title, price, description, then store it into a CSV, eventually making a Apify Actor out of it.

# Install all the dependencies.

- Install Python 😆
- [Install pipx](https://pipx.pypa.io/stable/installation/): `brew install pipx`
- [Install poetry](https://python-poetry.org/docs/): `pipx install poetry`
- [Install Crawlee](https://crawlee.dev/python/docs/quick-start): `python -m pip install 'crawlee[all]'`
- [Install Apify CLI](https://docs.apify.com/cli/): `npm i -g apify-cli`

# Project start

- run command: `pipx run 'crawlee[cli]' create nike-crawler`
- Select `Playwright` then `httpx` then `poetry` then enter start URL: `https://www.nike.com/` then `y` for the Apify integration prompt.
- `cd nike-crawler`
- in main.py file, set `headless = False` and `max_requests_per_crawl = 50`
- Now coming to routes.py, let's remove: `await context.enqueue_links()` and add these imports:
```py
import asyncio
from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router
from crawlee import Request
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from logging import Logger
```
- Run command: `sudo poetry run python3 -m nike_crawler`

# Handling cooking dialogue

- In many countries, there is a cookie dialog pop up which tries to block us from further scraping so we first need to get rid of it.
- add to routes.py file after :
```py
async def accept_cookies_if_present(page: Page, log: Logger) -> None:
    """
    Checks for a cookie dialogue and accepts it if it appears.

    Args:
        page: The Playwright Page object.
        log: The crawler's logger instance for consistent logging.
    """
    try:
        # Wait for the button to become visible, with a short timeout.
        # If the button doesn't appear within 3 seconds, a TimeoutError is raised.
        accept_button = page.get_by_test_id('dialog-accept-button')
        await accept_button.wait_for(state='visible', timeout=3000)
        await accept_button.click()
        log.info('Cookie dialogue found and accepted.')
    except PlaywrightTimeoutError:
        # If the button is not found, log that no cookie dialogue was present.
        log.info('No cookie dialogue found, proceeding without accepting cookies.')
```
- This will handle the cookies in every tab, if there is a cookie it will accept otherwise move on.
- Add `await accept_cookies_if_present(context.page, context.log)` to the `async def default_handler(context: PlaywrightCrawlingContext) -> None:`
- final code:
```py
import asyncio
from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router
from crawlee import Request
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from logging import Logger

router = Router[PlaywrightCrawlingContext]()

async def accept_cookies_if_present(page: Page, log: Logger) -> None:
    """
    Checks for a cookie dialogue and accepts it if it appears.

    Args:
        page: The Playwright Page object.
        log: The crawler's logger instance for consistent logging.
    """
    try:
        # Wait for the button to become visible, with a short timeout.
        # If the button doesn't appear within 3 seconds, a TimeoutError is raised.
        accept_button = page.get_by_test_id('dialog-accept-button')
        await accept_button.wait_for(state='visible', timeout=3000)
        await accept_button.click()
        log.info('Cookie dialogue found and accepted.')
    except PlaywrightTimeoutError:
        # If the button is not found, log that no cookie dialogue was present.
        log.info('No cookie dialogue found, proceeding without accepting cookies.')

@router.default_handler
async def default_handler(context: PlaywrightCrawlingContext) -> None:
    """Default request handler."""
    context.log.info(f'Processing {context.request.url} ...')
    await accept_cookies_if_present(context.page, context.log)

    title = await context.page.query_selector('title')
    await context.push_data(
        {
            'url': context.request.loaded_url,
            'title': await title.inner_text() if title else None,
        }
    )
```

# Adding all shoes listing 

- Let's use `get_by_test_id` with the filter of `has_text='All shoes'` and add all the links with the text “All shoes” to the request handler. Let's add this code to the existing `routes.py` file:
```py
shoe_listing_links = (
        await context.page.get_by_test_id('link').filter(has_text='All shoes').all()
    )

```
- remove:
```py
await context.push_data(
        {
            'url': context.request.loaded_url,
            'title': await title.inner_text() if title else None,
        }
    )
```
# Adding request for all shoe links:

- Add it to the current

```py
requests = []
    for link in shoe_listing_links:
        if (url := await link.get_attribute('href')):
            requests.append(Request.from_url(url, label='listing'))

    await context.add_requests(requests)
```

```py
await context.add_requests(
        [
            Request.from_url(url, label='listing')
            for link in shoe_listing_links
            if (url := await link.get_attribute('href'))
        ]
    )
```

# Extract data from product details

Now that we have all the links to the pages with the title “All Shoes,” the next step is to scrape all the products on each page and the information provided on them.

We'll extract each shoe's URL, title, price, and description. Again, let's go to dev tools and extract each parameter's relevant `test_id`. After scraping each of the parameters, we'll use the `context.push_data` function to add it to the local storage. Now let's add the following code to the `listing_handler` and update it in the `routes.py` file:

```py
@router.handler('listing')
async def listing_handler(context: PlaywrightCrawlingContext) -> None:
    """Handler for shoe listings."""
    # Handle the cookie dialogue before proceeding.
    await context.enqueue_links(selector='a.product-card__link-overlay', label='detail')



@router.handler('detail')
async def detail_handler(context: PlaywrightCrawlingContext) -> None:
    """Handler for shoe details."""
    # It's good practice to handle cookies on detail pages as well,
    # in case a user starts the crawl from a detail page URL.
    await accept_cookies_if_present(context.page, context.log)

    title = await context.page.get_by_test_id(
        'product_title',
    ).text_content()

    price = await context.page.get_by_test_id(
        'currentPrice-container',
    ).first.text_content()

    description = await context.page.get_by_test_id(
        'product-description',
    ).text_content()

    await context.push_data(
        {
            'url': context.request.loaded_url,
            'title': title,
            'price': price,
            'description': description,
        }
    )
```
# Handle infinite scrolling

To handle infinite scrolling in Crawlee for Python, we just need to make sure the page is loaded, which is done by waiting for the `network_idle` load state, and then use the `infinite_scroll` helper function which will keep scrolling to the bottom of the page as long as that makes additional items appear.


```py
@router.handler('listing')
async def listing_handler(context: PlaywrightCrawlingContext) -> None:
    """Handler for shoe listings."""
    await accept_cookies_if_present(context.page, context.log)
    await context.page.wait_for_load_state('networkidle')
    await context.infinite_scroll()
    await context.enqueue_links(
            selector='a.product-card__link-overlay', label='detail'
        )
```

# Export it to CSV

add this to `main.py` file:

`await crawler.export_data('shoes.csv')`

# Making an Actor 

- Create an .actor folder with the necessary files.

`mkdir .actor && touch .actor/{actor.json,input_schema.json}`

- Move the Dockerfile from the root folder to .actor.

`mv Dockerfile .actor`

- The actor.json file contains project metadata for the Apify platform. Follow the documentation for proper configuration:
```
{
  "actorSpecification": 1,
  "name": "Nike-Crawlee",
  "title": "Nike - Crawlee",
  "minMemoryMbytes": 2048,
  "description": "Scrape all shoes from nike website",
  "version": "0.1",
  "meta": {
    "templateId": "nike-crawlee"
  },
  "input": "./input_schema.json",
  "dockerfile": "./Dockerfile"
}
```
- Let's define input parameters for our crawler:

`maxItems` - this should be an externally configurable parameter.

```
{
    "title": "Nike Crawlee",
    "type": "object",
    "schemaVersion": 1,
    "properties": {
        "maxItems": {
            "type": "integer",
            "editor": "number",
            "title": "Limit search results",
            "description": "Limits the maximum number of results, applies to each search separately.",
            "default": 10
        }
```

- Let's update the code(`main.py`) to accept input parameters.


```py
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
```

# Deploying to Apify

Use the official Apify CLI to upload your code:

- Authenticate using your API token from Apify Console:

`apify login`

Choose "Enter API token manually" and paste your token.

Push the project to the platform:

`apify push`

Now you can configure runs on the Apify platform.





  
