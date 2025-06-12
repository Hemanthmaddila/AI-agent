import asyncio
import logging
from app.services.scrapers.linkedin_scraper import LinkedInScraper
from app.services.browser_automation_service import browser_service

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Output to console
    ]
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting LinkedIn Vision Apply Test Script...")

    # Initialize browser_service and start the browser (non-headless to observe)
    # Ensure browser_service attributes are initialized if they are None
    if browser_service.browser is None:
         logger.info("Browser service browser attribute was None, calling start_browser.")
         await browser_service.start_browser(headless=False)
    elif not browser_service.browser.is_connected():
        logger.info("Browser was not connected, calling start_browser.")
        await browser_service.start_browser(headless=False)
    else:
        logger.info("Browser service already has an active browser.")

    if not browser_service.page:
        logger.info("Browser service did not have a page, creating one.")
        if browser_service.browser and browser_service.browser.is_connected():
            await browser_service.new_page()
            logger.info(f"New page created. Current page URL: {browser_service.page.url if browser_service.page else 'N/A'}")
        else:
            logger.error("Browser not started or not connected, cannot create page.")
            return
    else:
        logger.info(f"Browser service already has a page. Current page URL: {browser_service.page.url}")


    scraper = LinkedInScraper()

    try:
        job_url = input("Enter LinkedIn Job URL to test application initiation: ")
        if not job_url:
            logger.warning("No job URL entered. Exiting.")
            return

        logger.info(f"Attempting to initiate application for: {job_url}")

        # The initiate_application_on_job_page method uses browser_service.page internally
        # It will navigate browser_service.page to job_url
        app_type, result_page, message = await scraper.initiate_application_on_job_page(job_url)

        logger.info(f"--- Application Initiation Result ---")
        logger.info(f"  Type: {app_type}")
        logger.info(f"  Message: {message}")

        # result_page could be the same as browser_service.page or a new page from context.expect_page
        if result_page:
            logger.info(f"  Result Page URL: {result_page.url}")
            if result_page != browser_service.page:
                logger.info(f"  Result page is different from browser_service.page. Ensure it's active if needed for next steps.")
                # await result_page.bring_to_front() # Example if you need to interact with it
        else:
            logger.info(f"  Result Page: Not available (None)")
            logger.info(f"  Current browser_service.page URL: {browser_service.page.url if browser_service.page else 'N/A'}")


        logger.info("Observe the browser. Script will close in 30 seconds. Press Ctrl+C in the console to exit sooner.")
        await asyncio.sleep(30)

    except KeyboardInterrupt:
        logger.info("Script interrupted by user (Ctrl+C).")
    except Exception as e:
        logger.error(f"An error occurred during the test: {e}", exc_info=True)
    finally:
        logger.info("Closing browser...")
        await browser_service.close_browser()
        logger.info("Browser closed. Test script finished.")

if __name__ == "__main__":
    asyncio.run(main())
