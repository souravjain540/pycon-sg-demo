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
    shoe_listing_links = (
        await context.page.get_by_test_id('link').filter(has_text='All shoes').all()
    )
    requests = []
    for link in shoe_listing_links:
        if (url := await link.get_attribute('href')):
            requests.append(Request.from_url(url, label='listing'))

    await context.add_requests(requests)

@router.handler('listing')
async def listing_handler(context: PlaywrightCrawlingContext) -> None:
    """Handler for shoe listings."""
    await accept_cookies_if_present(context.page, context.log)
    await context.page.wait_for_load_state('networkidle')
    await context.infinite_scroll()
    await context.enqueue_links(
            selector='a.product-card__link-overlay', label='detail'
        )


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
