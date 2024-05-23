# Packages
from logger_config import logger
import time
import json
from selenium.webdriver.common.by import By
import pyautogui
from markdownify import markdownify as md
import re

# Custom code 
from database_tools import DatabaseTools 
from selenium_base import SeleniumScraper, Browsers
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException, ElementNotInteractableException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



class KarriereScraper(SeleniumScraper):
    """Initializes the Indeed Scraper with the specified browser and database settings."""
    print('Karriere Scraper Initialized')
    def __init__(self, browser: str = Browsers.CHROME, use_database: bool = False):
        super().__init__(browser=browser, use_database=use_database)
        self.session_id = None

    """Type Parameters for Indeed Scraper"""
    class SortBy:
        DATE = 'date'
        RELEVANCE = 'relevance'

    """The URL Builder for Indeed Scraper"""

    def build_query_url(self,
                        keywords: str = None,  # job title, skills, etc
                        location: str = None,  # city, province, state or "Remote"
                        ):

        if keywords is None:
            raise ValueError('Keywords are required.')
        else:
            keywords = keywords.replace(' ', '%20')

        # This is the base url for all queries
        self.url = f"https://www.karriere.at/jobs?keywords={keywords}"

        # add location to the query
        if location is not None:
            self.url = f"{self.url}&l={location}"

        logger.info(f'URL built: {self.url}')
        # return the url
        return self.url

    """Parsing Functions"""
        
    def get_filter_items(self):
        """Returns the list of filter tags from an Indeed job search results list."""
        # self.load_all_jobs()
        menu_items = []
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                dropdowns = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, 'm-jobsFilterDropdown')))
                for dropdown in dropdowns:
                    try: 
                        button = dropdown.find_element(By.CSS_SELECTOR, "button")
                        if button.get_attribute('id').startswith('jobsFilter'):
                            # button.click()
                            self.driver.execute_script("arguments[0].click();", button)
                            WebDriverWait(self.driver, 5).until(
                            EC.visibility_of_all_elements_located((By.CLASS_NAME, 'm-checkbox__label.m-checkbox__label--light')))
                            options = [x.text for x in dropdown.find_elements(By.CLASS_NAME, 'm-checkbox__label.m-checkbox__label--light')]
                            # print(f"Dropdown: {dropdown}, Button: {button}, Options: {options}")
                            menu_item = {
                                'name': button.text,
                                'options': options
                            }
                            menu_items.append(menu_item)
                    except StaleElementReferenceException:
                        print(f"Stale element reference for dropdown: {dropdown}. Retrying within attempt.")
                        continue
                break
            except StaleElementReferenceException:
                print(f"Attempt {attempt + 1} failed due to StaleElementReferenceException. Retrying...")
                if "onetrust-consent-sdk" in self.driver.page_source:
                    self.close_cookie_popup(self)
            except TimeoutException as e:
                print(f"Attempt {attempt + 1} failed due to TimeoutException: {e}. Retrying...")
            except Exception as e:
                print(f"Attempt {attempt + 1} failed due to an unexpected exception: {e}. Retrying...")
        

        logger.info(f'Filter items found: {menu_items}'.encode('utf-8'))

        return menu_items
    
    def load_all_jobs(self):
        try:
            while True:
                try:
                    # Locate the button by its class name
                    load_more_button = self.driver.find_element(By.CLASS_NAME, 'm-loadMoreJobsButton__button')

                    # Use JavaScript to click the button
                    self.driver.execute_script("arguments[0].click();", load_more_button)
                    
                    # Optionally, wait for a few seconds to allow the new jobs to load
                    time.sleep(2)  # Adjust the sleep time if necessary

                except NoSuchElementException:
                    # If the button is no longer found, it means all jobs have been loaded
                    print("No more 'Load More' button found. All jobs are loaded.")
                    break
                except ElementNotInteractableException:
                    # If the button is found but not interactable, we should break as well
                    print("The 'Load More' button is no longer interactable.")
                    break
        except Exception as e:
            print(f"An error occurred: {e}")

    def get_current_url(self):
        logger.info(
            f'Getting current url: {self.driver.current_url}')
        return '&'.join(self.driver.current_url.split('&')[0:-2])

    """UI Manipulation Functions"""

    def close_popup(self):
        try:
            logger.info('Closing popup')
            self.driver.find_element(
                by=By.CSS_SELECTOR, value='button[aria-label="close"]').click()
            time.sleep(1)
        except:
            pass

    def click_next(self):
        logger.info('Clicking next page')
        self.driver.find_element(
            by=By.CSS_SELECTOR, value='a[data-testid="pagination-page-next"]').click()

    def click_prev(self):
        logger.info('Clicking previous page')
        self.driver.find_element(
            by=By.CSS_SELECTOR, value='a[data-testid="pagination-page-prev"]').click()

    def close_cookie_popup(self):
        """Close the cookie popup if it appears."""
        try:
            # cookie_popup = self.driver.find_elements(By.ID, 'onetrust-consent-sdk')
            close_button = self.driver.find_element(By.CLASS_NAME, 'onetrust-close-btn-handler')
            close_button.click()
            logger.info("Closed cookie popup")
            WebDriverWait(self.driver, 5).until(
                EC.invisibility_of_element_located((By.ID, 'onetrust-close-btn-container'))
            )
            print("Cookie popup closed")
        except TimeoutException:
            print("No cookie popup found or popup did not close in time")
        except NoSuchElementException:
            print("No cookie popup found")


    # !!!! TODO: This function doesnt work on all resolutions and browsers. Also it should minimize back. Full-screen indeed is bright.
    def requires_human_verification(self):
        logger.info('Checking for human verification')
        # works on 1080 * 1920 resolution, with firefox browser
        if 'Verify' in str(self.driver.page_source):
            logger.info('Human verification required')
            self.driver.fullscreen_window()
            time.sleep(2)
            where = {
                Browsers.FIREFOX: {'x': 537, 'y': 286}
            }
            pyautogui.click(where[self.browser]['x'], where[self.browser]['y'])
            time.sleep(2)
            self.driver.minimize_window()
            return True
        else:
            return False

    """Main Functions"""

    def search_for_jobs(self, **search_params):
        """Collects job listings from the current page and returns them as a list of dictionaries."""

        self.open_browser(wait_seconds=0)

        self.url = self.build_query_url(**search_params)

        self.go_to_url(self.url)

        time.sleep(15)
        # self.driver.implicitly_wait(10)

        self.close_cookie_popup()

        self.load_all_jobs()

        time.sleep(1)
        # filter_items = self.get_filter_items()
        

        # create a new search session record in the database
        db_tools = DatabaseTools()
        self.session_id = db_tools.start_new_session(
            terms=search_params['keywords'],
            location=search_params['location']
            # filter_tags=str(json.dumps(filter_items))
        )
        
        global sess_id 
        sess_id= self.session_id
        

        # Isolate the job cards on the page. Each card is a job listing.
        job_cards = self.driver.find_elements(
            By.CLASS_NAME, 'm-jobsList__item')

        for job in job_cards:

            try:  # to get the unique id of the job
                job_unique_id = job.find_element(By.CLASS_NAME, 'm-jobsListItem').get_attribute('data-id')
            except:
                job_unique_id = None

            try:  # to get the job title
                job_title = job.find_element(
                    By.CLASS_NAME, 'm-jobsListItem__titleLink').text
            except:
                print('no job title')
                job_title = None

            try:  # to get the job link
                job_link = job.find_element(
                    By.TAG_NAME, 'a').get_attribute('href')
            except:
                print('no job link')
                job_link = None

            try:  # to get the company name
                job_company = job.find_element(By.CLASS_NAME, 'm-jobsListItem__companyName').text
            except:
                job_company = None

            try:  # to get the company name
                job_location = job.find_element(By.CLASS_NAME, 'm-jobsListItem__location').text
            except:
                job_location = None

            # Build the job object
            obj = {
                'job_unique_id': job_unique_id,
                'job_title': job_title,
                'job_link': job_link,
                'session_id': self.session_id,
                'job_company': job_company,
                'job_location': job_location
            }
            db = DatabaseTools()
            db.update_job_postings(obj)

        # Prepare to switch pages. Saving the last working link is helful for error handling.
        self.previous_url = self.get_current_url()

        # current_page += 1
        self.close_browser()

    """Obtaining and parsing the job description from the job page."""

    def get_job_html(self, url: str):

        def get_description_html():
            try:
                description_element = self.driver.find_element(
                    By.CLASS_NAME, 'jobsearch-JobComponent')
                return description_element.get_attribute('innerHTML')
            except:
                
                # Sometimes in indeed the job description links out to a different website, and not the "jobsearch-JobComponent" class.
                # This is a workaround to get the job description in those cases. We'll just get the entire page.
                ele = self.driver.find_element(By.TAG_NAME, 'body').get_attribute('innerHTML')
                if 'Verifying you are human' in ele:
                    time.sleep(1)
                    self.requires_human_verification()
                else:
                    return ele
        self.go_to_url(url)

        try:
            description_html = get_description_html()

        except:
            self.requires_human_verification()
            try:
                description_html = get_description_html()
            except:
                time.sleep(3)
                self.requires_human_verification()
                description_html = get_description_html()

        return description_html

    def html_to_markdown(self, description_html: str):
        md_text = md(description_html)
        # logger.debug(md_text.encode('utf-8'))
        return md_text

    def remove_links_from_markdown(self, markdown, replace_with: str = '<url removed>'):
        def replace_link(match):
            return f"[{match.group(1)}]({replace_with})"
        pattern = r'\[([^]]+)]\(([^)]+)\)'
        return re.sub(pattern, replace_link, markdown).replace('\n', '')

    def updating_job_postings(self, df):
        scraper = KarriereScraper(browser=Browsers.FIREFOX, use_database=False)
        db = DatabaseTools()
        print(f'Updating {len(df.index)} job postings.')
        scraper.open_browser()
        for index, row in df.iterrows():
            # job number and url
            print(f'Job {index+1} of {len(df.index)}: {row["job_link"]}')
            job_html = scraper.get_job_html(row['job_link'])
            if job_html is not None:
                job_markdown = scraper.html_to_markdown(job_html)
                db.update_job_posting_description(
                    row['job_unique_id'], job_markdown)
        scraper.close_browser()
        print('All job postings updated.')

def main(dont_search=False, dont_update_job_descriptions=False, **search_params):
    print(f'Searching for {search_params["keywords"]} jobs in {search_params["location"]}.')
    # Run the Scraper to collect job postings
    scraper = KarriereScraper(browser=Browsers.FIREFOX, use_database=False)
   
    if dont_search:
        print(f'Skipping search. Only updating job descriptions.')
    else:
        print(f'Searching for job postings.')
        scraper.search_for_jobs(**search_params)

    if dont_update_job_descriptions:
        print('Skipping job description updates.')
    else:
        # Determine which job postings need to be updated
        db = DatabaseTools()
        # df = db.sql_to_df(
            # '''SELECT * FROM job_postings WHERE 
            # (job_description IS NULL or job_description like '' 
            # or job_description like 'Verify% you are human'
            # or job_description like '%nable JavaScript%') 
            # and job_link is not null''')
        df = db.sql_to_df('''SELECT * FROM job_postings''')
        # df = db.get_postings_by_session(sess_id)
        # print(df.tail(10))
        if len(df.index) == 0:
            print('No job postings to update.')
            exit()

        # For each job posting without a description, get the description from the job link and update the database.
        # print(f'Updating {len(df.index)} job postings.')
        # scraper.open_browser()
        # for index, row in df.iterrows():
        #     # job number and url
        #     print(f'Job {index+1} of {len(df.index)}: {row["job_link"]}')
        #     job_html = scraper.get_job_html(row['job_link'])
        #     if job_html is not None:
        #         job_markdown = scraper.html_to_markdown(job_html)
        #         db.update_job_posting_description(
        #             row['job_unique_id'], job_markdown)
        # scraper.close_browser()
        # print('All job postings updated.')
        


    print("Writing recentt search to csv!!")
    # df_final = db.sql_to_df("select * from job_postings where date(timestamp) = date('now')")
    # df_search_sessions = db.sql_to_df("select * from search_sessions")
    # df_recent_session_id = df_search_sessions['id'].tail(1).item()

    term = search_params['keywords']
    loc = search_params['location']

    # df_final = df_final.loc[df_final['session_id'] == df_recent_session_id]

    df.to_csv(f'job_postings_austria_{term}_{loc}.csv')
    print("writing complete")

    
    
    