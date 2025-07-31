import requests
import time
import sys
from typing import Optional


def download_with_retry(url: str, 
                       output_file: str = None,
                       timeout: int = 30,
                       max_retries: int = 3,
                       retry_delay: float = 1.0,
                       context: str = "") -> Optional[requests.Response]:
    """
    Download content from URL with retry logic and timeout.
    
    Args:
        url: URL to download from
        output_file: If provided, save content to this file
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        context: Context string for error messages
        
    Returns:
        Response object if successful, None if all retries failed
    """
    context_msg = f" ({context})" if context else ""
    
    for attempt in range(max_retries + 1):
        try:
            print(f"Downloading {url}{context_msg}... (attempt {attempt + 1}/{max_retries + 1})")
            
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Tax Software Slovenia)'
                }
            )
            response.raise_for_status()
            
            # If output file specified, save content
            if output_file:
                with open(output_file, "wb") as f:
                    f.write(response.content)
                print(f"Successfully downloaded to {output_file}")
            
            return response
            
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                print(f"Request timed out after {timeout}s, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Error: Download failed after {max_retries + 1} attempts - request timed out")
                print(f"The server at {url} is not responding within {timeout} seconds")
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries:
                print(f"Connection failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"Error: Cannot connect to {url} after {max_retries + 1} attempts")
                print("Please check your internet connection")
                
        except requests.exceptions.HTTPError as e:
            print(f"Error: HTTP {e.response.status_code} - {e.response.reason}")
            if e.response.status_code >= 500:
                # Server error - retry
                if attempt < max_retries:
                    print(f"Server error, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"Server error persists after {max_retries + 1} attempts")
            else:
                # Client error - don't retry
                print("This appears to be a client error (4xx) - not retrying")
                break
                
        except Exception as e:
            print(f"Error downloading from {url}: {e}")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"Download failed after {max_retries + 1} attempts")
    
    return None


def download_or_exit(url: str,
                    output_file: str = None,
                    timeout: int = 30,
                    max_retries: int = 3,
                    context: str = "") -> requests.Response:
    """
    Download content from URL or exit the application if it fails.
    
    This is a wrapper around download_with_retry that exits the application
    if the download fails, which is appropriate for critical resources.
    
    Args:
        url: URL to download from
        output_file: If provided, save content to this file
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        context: Context string for error messages
        
    Returns:
        Response object (never returns None - exits on failure)
    """
    response = download_with_retry(
        url=url,
        output_file=output_file,
        timeout=timeout,
        max_retries=max_retries,
        context=context
    )
    
    if response is None:
        context_msg = f" for {context}" if context else ""
        print(f"Fatal error: Could not download required resource{context_msg}")
        print(f"URL: {url}")
        print("Cannot continue without this resource")
        sys.exit(1)
    
    return response


def validate_download(file_path: str, min_size: int = 100, context: str = ""):
    """
    Validate that a downloaded file exists and has reasonable content.
    
    Args:
        file_path: Path to the downloaded file
        min_size: Minimum expected file size in bytes
        context: Context string for error messages
    """
    import os
    
    context_msg = f" ({context})" if context else ""
    
    if not os.path.exists(file_path):
        print(f"Error: Downloaded file {file_path} does not exist{context_msg}")
        sys.exit(1)
    
    file_size = os.path.getsize(file_path)
    if file_size < min_size:
        print(f"Error: Downloaded file {file_path} is too small ({file_size} bytes){context_msg}")
        print(f"Expected at least {min_size} bytes")
        print("The download may have failed or returned an error page")
        sys.exit(1)
    
    print(f"Downloaded file validated: {file_path} ({file_size} bytes)")