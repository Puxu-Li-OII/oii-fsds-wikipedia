import argparse
from datetime import datetime
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import os

DATA_DIR = Path("data")

def download_page_w_revisions(page_title: str) -> str:
    """Downloads complete revision history of a page using Special:Export with progress bar."""
    url = f"https://en.wikipedia.org/wiki/Special:Export/{page_title}"
    params = {
        "history": "",  # Empty parameter to get full history
        "action": "submit"
    }
    
    # Make initial request to get content length
    response = requests.get(url, params=params, stream=True)
    response.raise_for_status()
    
    # Get total size if available
    total_size = int(response.headers.get('content-length', 0))
    
    # Initialize progress bar
    progress = tqdm(
        total=total_size,
        unit='iB',
        unit_scale=True,
        desc="Downloading revisions",
        leave=True
    )
    
    # Download with progress
    content = []
    for data in response.iter_content(chunk_size=8192):
        content.append(data)
        progress.update(len(data))
    
    progress.close()
    
    return b''.join(content).decode('utf-8')

def parse_mediawiki_revisions(xml_content):
    soup = BeautifulSoup(xml_content, "lxml-xml")
    for revision in soup.find_all("revision"):
        yield str(revision)

def count_revisions_in_xml(xml_content: str) -> int:
    """Count the number of revisions in a single XML response."""
    soup = BeautifulSoup(xml_content, "lxml-xml")
    return len(soup.find_all("revision"))

def count_stored_revisions(page_name: str, data_dir: Path) -> dict:
    """
    Counts all stored revisions for a given page, organized by year and month.
    
    Returns:
        dict: A dictionary with total count and breakdowns by year and month
        Format: {
            'total': int,
            'by_year': {year: count, ...},
            'by_year_month': {(year, month): count, ...}
        }
    """
    page_dir = data_dir / page_name
    if not page_dir.exists():
        return {'total': 0, 'by_year': {}, 'by_year_month': {}}
    
    counts = {
        'total': 0,
        'by_year': {},
        'by_year_month': {}
    }
    
    # Walk through the directory structure
    for year_dir in sorted(page_dir.iterdir()):
        if not year_dir.is_dir():
            continue
            
        year = year_dir.name
        counts['by_year'][year] = 0
        
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
                
            month = month_dir.name
            revision_count = len(list(month_dir.glob("*.xml")))
            
            counts['by_year'][year] += revision_count
            counts['by_year_month'][(year, month)] = revision_count
            counts['total'] += revision_count
    
    return counts

def format_revision_counts(page_name: str, counts: dict) -> str:
    """Formats the revision counts into a readable string."""
    if counts['total'] == 0:
        return f"No revisions found for '{page_name}'."
    
    # Basic summary
    output = [f"Found {counts['total']} total revisions for '{page_name}'."]
    
    # Year breakdown
    year_counts = counts['by_year']
    if year_counts:
        output.append("\nBreakdown by year:")
        for year in sorted(year_counts.keys()):
            output.append(f"  {year}: {year_counts[year]} revisions")
    
    # Month breakdown (optional, commented out to avoid too much detail)
    # month_counts = counts['by_year_month']
    # if month_counts:
    #     output.append("\nBreakdown by month:")
    #     for (year, month) in sorted(month_counts.keys()):
    #         output.append(f"  {year}-{month}: {month_counts[(year, month)]} revisions")
    
    return "\n".join(output)

def main(page: str, data_dir: Path, count_only: bool = False):
    """
    Downloads all revisions of the given page title and organizes them by date.
    If count_only is True, just prints the count of stored revisions.
    """
    if count_only:
        counts = count_stored_revisions(page, data_dir)
        print(format_revision_counts(page, counts))
        return

    print(f"Downloading complete history of {page}")
    raw_revisions = download_page_w_revisions(page)
    
    # Count total revisions for progress bar
    total_revisions = len(BeautifulSoup(raw_revisions, "lxml-xml").find_all("revision"))
    print(f"Found {total_revisions} revisions. Organizing into directory structure...")
    
    for wiki_revision in tqdm(parse_mediawiki_revisions(raw_revisions), total=total_revisions):
        revision_path = construct_path(
            wiki_revision=wiki_revision, page_name=page, save_dir=data_dir
        )
        if not revision_path.exists():
            revision_path.parent.mkdir(parents=True, exist_ok=True)
            revision_path.write_text(wiki_revision)
    
    # Show final counts
    counts = count_stored_revisions(page, data_dir)
    print("\nFinal revision counts:")
    print(format_revision_counts(page, counts))


def extract_id(revision: str) -> str:
    return str(_extract_attribute(revision, attribute="id"))


def find_timestamp(revision: str) -> datetime:
    return parse_timestring(_extract_attribute(revision, attribute="timestamp"))


def _extract_attribute(text: str, attribute: str = "timestamp") -> str:
    soup = BeautifulSoup(text, "lxml-xml")
    result = soup.find(attribute)
    if result is None:
        raise ValueError(f"Could not find attribute {attribute} in text")
    return result.text


def parse_timestring(timestring: str) -> datetime:
    return datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%SZ")


def extract_yearmonth(timestamp: datetime) -> str:
    return timestamp.strftime("%Y-%m")


def find_yearmonth(revision: str) -> str:
    return extract_yearmonth(find_timestamp(revision))

<<<<<<< HEAD

def main(page: str, limit: int, folders: bool, update: bool, data_dir: Path):
    """
    Downloads the main page (with revisions) for the given page title.
    Organizes the revisions into a folder structure like
    <page_name>/<year>/<month>/<revision_id>.xml
    """

    if update == 'True':
        print(f"Downloading {limit} revisions of {page} to {data_dir}")
        raw_revisions = download_page_w_revisions(page, limit=limit)
        validate_page(page, page_xml=raw_revisions)
        print("Downloaded revisions. Parsing and saving...")
        for wiki_revision in tqdm(parse_mediawiki_revisions(raw_revisions), total=limit):
            revision_path = construct_path(
                wiki_revision=wiki_revision, page_name=page, save_dir=data_dir
            )
            if not revision_path.exists():
                revision_path.parent.mkdir(parents=True, exist_ok=True)
            revision_path.write_text(wiki_revision)
        
        revision_data_saving_path = data_dir / page
        files_num = count_revisions(revision_data_saving_path, folders)
        if folders == 'False':
            print(f"The number of files downloaded: {files_num}")
        else:
            print(f"The number of files including the folders: {files_num}")
        print("Done!") # You should call count_revisions() here and print the number of revisions
                    # You should also pass an 'update' argument so that you can decide whether
                    # to update and refresh or whether to simply count the revisions.   
    else:
        print(f"Only count the files in the revision folder: \"./{data_dir}/{page}\"")
        revision_data_saving_path = data_dir / page
        files_num = count_revisions(revision_data_saving_path, folders)
        if folders == 'False':
            print(f"The number of files downloaded: {files_num}")
        else:
            print(f"The number of files including the folders: {files_num}")


=======
>>>>>>> upstream/main
def construct_path(page_name: str, save_dir: Path, wiki_revision: str) -> Path:
    revision_id = extract_id(wiki_revision)
    timestamp = find_timestamp(wiki_revision)
    year = str(timestamp.year)
    month = str(timestamp.month).zfill(2)
    revision_path = save_dir / page_name / year / month / f"{revision_id}.xml"
    return revision_path


def validate_page(page_name: str, page_xml: str) -> None:
    try:
        _ = _extract_attribute(page_xml, attribute="page")
    except ValueError:
        raise ValueError(f"Page {page_name} does not exist")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download Wikipedia page revisions",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("page", type=str, help="Title of the Wikipedia page")
    parser.add_argument(
        "--count-only",
        action="store_true",
        help="Only count and display stored revisions without downloading",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory to store the revision data",
    )
    parser.add_argument(
        "--folders",
        type=str,
        default='False',
        help="Whether to count the folders",
    )
    parser.add_argument(
        "--update",
        type=str,
        default='True',
        help="Whether to update",
    )
    args = parser.parse_args()
<<<<<<< HEAD
    main(page=args.page, limit=args.limit, folders=args.folders, update=args.update, data_dir=DATA_DIR)
=======
    main(page=args.page, data_dir=args.data_dir, count_only=args.count_only)
>>>>>>> upstream/main
