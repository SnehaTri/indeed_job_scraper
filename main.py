import argparse
import logging
from karriere_scraper import KarriereScraper, main  # Adjust this import based on your actual module structure.




def parse_args():
    parser = argparse.ArgumentParser(description="Scrape job listings from Karriere.")
    parser.add_argument('--keywords', type=str, default='Data Scientist', help='Keywords to search for.')
    parser.add_argument('--location', type=str, default='Austria', help='Location to search in.')
    parser.add_argument('--dont_search', action='store_true', help='Disable searching for new jobs.')
    parser.add_argument('--dont_update_job_descriptions', action='store_true', help='Disable updating job descriptions.')
    return parser.parse_args()

if __name__ == '__main__':

    args = parse_args()

    # Construct the search parameters Object
    search_params = {
        'keywords': args.keywords,
        'location': args.location,
    }

    # Run the main function with the parsed command line arguments.
    main(

        dont_search=args.dont_search, 
        dont_update_job_descriptions=args.dont_update_job_descriptions,
        **search_params
    )
    
    # Handle temporary bug fix with the second call
    if args.dont_update_job_descriptions:  # Check if updating descriptions is needed
        main(
        
            dont_search=args.dont_search, 
            dont_update_job_descriptions=False, 
            **search_params
        )
# python main.py --keywords "Engineering" --location "Toronto" --country CANADA --sort_by relevance --max_pages 2 --dont_search --dont_update_job_descriptions