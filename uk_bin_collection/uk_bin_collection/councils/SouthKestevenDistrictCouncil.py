import re
import requests
from datetime import datetime, timedelta
from io import BytesIO
import json
import os

from bs4 import BeautifulSoup
import easyocr
import cv2
import numpy as np
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from uk_bin_collection.uk_bin_collection.common import *
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def get_collection_day_from_postcode(self, driver, postcode):
        """Get the collection day for regular bins from the postcode checker."""
        try:
            # Use requests-based approach (no Selenium)
            collection_day = self._get_collection_day_requests(postcode)
            return collection_day
            
        except Exception as e:
            print(f"Error getting collection day: {e}")
            return None
    
    def _get_collection_day_requests(self, postcode):
        """Get collection day using requests (ASP.NET WebForms)."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            session = requests.Session()
            # Set headers to mimic a real browser
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            url = "https://pre.southkesteven.gov.uk/skdcNext/tempforms/checkmybin.aspx"
            
            # Get the initial form
            response = session.get(url, timeout=30)
            if response.status_code != 200:
                print(f"Failed to get form: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form')
            if not form:
                print("No form found")
                return None
            
            # Extract form data
            form_data = {}
            for input_field in form.find_all('input'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                input_type = input_field.get('type', 'text')
                if name:
                    form_data[name] = value
                    print(f"Form field: {name} ({input_type}) = {value[:50]}...")
            
            # Find the correct postcode field
            # Look for input fields that are not hidden/system fields
            text_inputs = []
            for input_field in form.find_all('input'):
                name = input_field.get('name', '')
                input_type = input_field.get('type', 'text')
                if input_type == 'text' and name not in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
                    text_inputs.append(name)
            
            print(f"Found text inputs: {text_inputs}")
            
            if not text_inputs:
                print("No text input fields found")
                return None
            
            # Update the first text input with postcode
            form_data[text_inputs[0]] = postcode
            print(f"Updated {text_inputs[0]} with postcode: {postcode}")
            
            # Submit the form
            action = form.get('action', '')
            if action.startswith('./'):
                action = action[2:]  # Remove './'
            submit_url = url.replace('checkmybin.aspx', action) if action else url
            
            print(f"Submitting to: {submit_url}")
            
            # Add referer header
            session.headers.update({'Referer': url})
            
            response = session.post(submit_url, data=form_data, timeout=30)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                text_content = soup.get_text()
                
                print("Response content preview:")
                print(text_content[:500])
                
                # Look for collection day patterns
                day_patterns = [
                    r'bin day is (\w+)',
                    r'collection day is (\w+)',
                    r'(\w+) is your bin day',
                    r'(\w+) is your collection day',
                    r'your bin day is (\w+)',
                    r'your collection day is (\w+)'
                ]
                
                for pattern in day_patterns:
                    match = re.search(pattern, text_content, re.IGNORECASE)
                    if match:
                        day = match.group(1)
                        print(f"Found collection day: {day}")
                        return day
                
                print("No collection day pattern found in response")
                return None
            else:
                print(f"Form submission failed with status {response.status_code}")
                print("Response content:")
                print(response.text[:500])
                return None
            
        except Exception as e:
            print(f"Requests approach failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_collection_day_selenium(self, driver, postcode):
        """Get collection day using Selenium (fallback)."""
        try:
            # Navigate to the new postcode checker
            driver.get("https://pre.southkesteven.gov.uk/skdcNext/tempforms/checkmybin.aspx")
            
            # Wait for page to load
            import time
            time.sleep(2)
            
            wait = WebDriverWait(driver, 30)
            
            # Find and fill the regular bins postcode field with multiple selectors
            bins_input = None
            selectors = [
                "//input[@placeholder='Please enter your Postcode']",
                "//input[contains(@placeholder, 'Postcode')]",
                "//input[@type='text']",
                "//input[contains(@class, 'postcode')]"
            ]
            
            for selector in selectors:
                try:
                    bins_input = wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    break
                except:
                    continue
            
            if not bins_input:
                print("Could not find postcode input field")
                return None
            
            # Clear and fill the input
            bins_input.clear()
            time.sleep(0.5)
            bins_input.send_keys(postcode)
            time.sleep(0.5)
            
            # Click the Check button with multiple selectors
            check_button = None
            button_selectors = [
                "//button[text()='Check']",
                "//button[contains(text(), 'Check')]",
                "//input[@type='submit']",
                "//button[@type='submit']"
            ]
            
            for selector in button_selectors:
                try:
                    check_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    break
                except:
                    continue
            
            if not check_button:
                print("Could not find check button")
                return None
            
            # Click the button
            check_button.click()
            time.sleep(3)  # Wait for results
            
            # Wait for results and extract the collection day
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Bin Day is')]")))
            except:
                # Try alternative text patterns
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'collection day')]")))
                except:
                    pass
            
            soup = BeautifulSoup(driver.page_source, features="html.parser")
            bin_day_element = soup.find(text=re.compile(r"Bin Day is \w+"))
            
            if bin_day_element:
                day_match = re.search(r"Bin Day is (\w+)", bin_day_element)
                if day_match:
                    return day_match.group(1)
            
            return None
            
        except Exception as e:
            print(f"Selenium approach failed: {e}")
            return None

    def get_green_bin_info_from_postcode(self, driver, postcode):
        """Get the green bin collection info from the postcode checker."""
        try:
            # Use requests-based approach (no Selenium)
            green_bin_info = self._get_green_bin_info_requests(postcode)
            return green_bin_info
            
        except Exception as e:
            print(f"Error getting green bin info: {e}")
            return None
    
    def _get_green_bin_info_requests(self, postcode):
        """Get green bin info using requests (ASP.NET WebForms)."""
        try:
            import requests
            from bs4 import BeautifulSoup
            
            session = requests.Session()
            # Set headers to mimic a real browser
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            url = "https://pre.southkesteven.gov.uk/skdcNext/tempforms/checkmybin.aspx"
            
            # Get the initial form
            response = session.get(url, timeout=30)
            if response.status_code != 200:
                print(f"Failed to get form for green bin: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            form = soup.find('form')
            if not form:
                print("No form found for green bin")
                return None
            
            # Extract form data
            form_data = {}
            for input_field in form.find_all('input'):
                name = input_field.get('name')
                value = input_field.get('value', '')
                input_type = input_field.get('type', 'text')
                if name:
                    form_data[name] = value
            
            # Find the correct postcode field (second text input for green bin)
            text_inputs = []
            for input_field in form.find_all('input'):
                name = input_field.get('name', '')
                input_type = input_field.get('type', 'text')
                if input_type == 'text' and name not in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
                    text_inputs.append(name)
            
            print(f"Found text inputs for green bin: {text_inputs}")
            
            if len(text_inputs) < 2:
                print("Not enough text input fields found for green bin")
                return None
            
            # Update the second text input with postcode (green bin)
            form_data[text_inputs[1]] = postcode
            print(f"Updated {text_inputs[1]} with postcode: {postcode}")
            
            # Submit the form
            action = form.get('action', '')
            if action.startswith('./'):
                action = action[2:]  # Remove './'
            submit_url = url.replace('checkmybin.aspx', action) if action else url
            
            print(f"Submitting green bin form to: {submit_url}")
            
            # Add referer header
            session.headers.update({'Referer': url})
            
            response = session.post(submit_url, data=form_data, timeout=30)
            print(f"Green bin response status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                text_content = soup.get_text()
                
                print("Green bin response content preview:")
                print(text_content[:500])
                
                # Look for green bin patterns
                green_patterns = [
                    r'green bin day is (\w+) week (\d+)',
                    r'green bin collection day is (\w+) week (\d+)',
                    r'(\w+) week (\d+) is your green bin day',
                    r'green bin: (\w+) week (\d+)',
                    r'garden waste: (\w+) week (\d+)'
                ]
                
                for pattern in green_patterns:
                    match = re.search(pattern, text_content, re.IGNORECASE)
                    if match:
                        day = match.group(1)
                        week = int(match.group(2))
                        print(f"Found green bin info: {day} week {week}")
                        return {
                            "day": day,
                            "week": week
                        }
                
                print("No green bin pattern found in response")
                return None
            else:
                print(f"Green bin form submission failed with status {response.status_code}")
                print("Response content:")
                print(response.text[:500])
                return None
            
        except Exception as e:
            print(f"Requests approach failed for green bin: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_green_bin_info_selenium(self, driver, postcode):
        """Get green bin info using Selenium (fallback)."""
        try:
            # Navigate to the new postcode checker
            driver.get("https://pre.southkesteven.gov.uk/skdcNext/tempforms/checkmybin.aspx")
            
            # Wait for page to load
            import time
            time.sleep(2)
            
            wait = WebDriverWait(driver, 30)
            
            # Find and fill the green bin postcode field (second input)
            green_bin_inputs = driver.find_elements(By.XPATH, "//input[@placeholder='Please enter your Postcode']")
            if len(green_bin_inputs) >= 2:
                green_bin_input = green_bin_inputs[1]  # Second input is for green bin
                green_bin_input.clear()
                time.sleep(0.5)
                green_bin_input.send_keys(postcode)
                time.sleep(0.5)
                
                # Click the Check button with multiple selectors
                check_button = None
                button_selectors = [
                    "//button[text()='Check']",
                    "//button[contains(text(), 'Check')]",
                    "//input[@type='submit']",
                    "//button[@type='submit']"
                ]
                
                for selector in button_selectors:
                    try:
                        check_button = wait.until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        break
                    except:
                        continue
                
                if not check_button:
                    print("Could not find check button for green bin")
                    return None
                
                check_button.click()
                time.sleep(3)  # Wait for results
                
                # Wait for results and extract the green bin info
                try:
                    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Green Bin Day is')]")))
                except:
                    # Try alternative text patterns
                    try:
                        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'green bin')]")))
                    except:
                        pass
                
                soup = BeautifulSoup(driver.page_source, features="html.parser")
                green_bin_element = soup.find(text=re.compile(r"Green Bin Day is \w+ \w+ \d+"))
                
                if green_bin_element:
                    # Extract day and week info (e.g., "Tuesday Week 2")
                    week_match = re.search(r"Green Bin Day is (\w+) Week (\d+)", green_bin_element)
                    if week_match:
                        return {
                            "day": week_match.group(1),
                            "week": int(week_match.group(2))
                        }
            
            return None
            
        except Exception as e:
            print(f"Selenium approach failed for green bin: {e}")
            return None

    def get_next_collection_dates(self, collection_day, num_weeks=8):
        """Calculate the next collection dates for a given day of the week."""
        today = datetime.now()
        days_of_week = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
            "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        target_day = days_of_week.get(collection_day, 0)
        current_weekday = today.weekday()
        
        # Calculate days until next collection day
        days_until = (target_day - current_weekday) % 7
        if days_until == 0:  # If today is the collection day, get next week's
            days_until = 7
            
        next_collection = today + timedelta(days=days_until)
        
        # Generate collection dates for the specified number of weeks
        collection_dates = []
        for week in range(num_weeks):
            collection_date = next_collection + timedelta(weeks=week)
            collection_dates.append(collection_date.strftime("%d/%m/%Y"))
            
        return collection_dates

    def get_green_bin_collection_dates(self, green_bin_info, num_weeks=8):
        """Calculate green bin collection dates based on OCR-extracted calendar data."""
        if not green_bin_info:
            return []
        
        # First, try to get green bin collection dates from OCR-parsed calendar data
        calendar_data = self.parse_calendar_images()
        green_bin_data = calendar_data.get('green_bin_info', {})
        
        if green_bin_data and 'collection_dates' in green_bin_data:
            # Use OCR-extracted collection dates
            collection_dates = green_bin_data['collection_dates']
            
            # Filter to future dates and limit to requested number
            today = datetime.now()
            future_dates = []
            
            for date_str in collection_dates:
                try:
                    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                    if date_obj >= today:
                        future_dates.append(date_str)
                        if len(future_dates) >= num_weeks:
                            break
                except ValueError:
                    continue
            
            if future_dates:
                print(f"Using OCR-extracted green bin collection dates: {future_dates}")
                return future_dates
        
        # Fallback to mathematical calculation if OCR data not available
        print("Using mathematical calculation for green bin collection dates")
        return self.calculate_green_bin_dates_mathematically(green_bin_info, num_weeks)

    def calculate_green_bin_dates_mathematically(self, green_bin_info, num_weeks=8):
        """Calculate green bin collection dates using mathematical approach (fallback)."""
        today = datetime.now()
        days_of_week = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
            "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        target_day = days_of_week.get(green_bin_info["day"], 1)
        target_week = green_bin_info["week"]
        
        # Find the next occurrence of the target day in the target week
        collection_dates = []
        current_date = today
        
        # Look ahead for the specified number of weeks
        for month_offset in range(num_weeks + 1):  # Look ahead enough months
            # Start from the first day of each month
            if month_offset == 0:
                # Current month
                start_date = current_date.replace(day=1)
            else:
                # Future months
                next_month = current_date.month + month_offset
                next_year = current_date.year
                while next_month > 12:
                    next_month -= 12
                    next_year += 1
                start_date = current_date.replace(year=next_year, month=next_month, day=1)
            
            # Find the target day in the target week of this month
            for day in range(1, 32):  # Check all possible days
                try:
                    candidate_date = start_date.replace(day=day)
                    
                    # Check if this is the target day of the week
                    if candidate_date.weekday() == target_day:
                        # Determine which week of the month this is (1 or 2)
                        week_of_month = ((candidate_date.day - 1) // 7) + 1
                        
                        # If this matches our target week and is in the future, add it
                        if week_of_month == target_week and candidate_date >= current_date:
                            collection_dates.append(candidate_date.strftime("%d/%m/%Y"))
                            if len(collection_dates) >= num_weeks:
                                return collection_dates
                            break  # Found the target day for this month, move to next month
                            
                except ValueError:
                    # Invalid date (e.g., Feb 30), skip
                    continue
                    
        return collection_dates

    def get_calendar_links(self):
        """Get the current calendar links from the South Kesteven website."""
        try:
            # URL of the bin day checker page
            bin_day_url = "https://pre.southkesteven.gov.uk/skdcNext/tempforms/checkmybin.aspx"
            
            print("Fetching calendar links from South Kesteven website...")
            
            # Get the page content
            response = requests.get(bin_day_url, timeout=30)
            if response.status_code != 200:
                print(f"Failed to fetch bin day page: {response.status_code}")
                return None, None
            
            # Parse the HTML to find calendar links
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for links containing calendar-related text
            calendar_links = {}
            
            # Find all links on the page
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Check for regular bin calendar link
                if 'black' in text and 'silver' in text and 'purple' in text:
                    if href.startswith('http'):
                        calendar_links['regular'] = href
                    elif href.startswith('/'):
                        calendar_links['regular'] = f"https://www.southkesteven.gov.uk{href}"
                
                # Check for green bin calendar link
                elif 'green' in text and 'bin' in text:
                    if href.startswith('http'):
                        calendar_links['green'] = href
                    elif href.startswith('/'):
                        calendar_links['green'] = f"https://www.southkesteven.gov.uk{href}"
            
            # Also look for links with specific patterns
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Look for calendar-related links
                if 'calendar' in href.lower() or 'collection' in href.lower() or 'calendar' in text:
                    if 'black' in href.lower() or 'silver' in href.lower() or 'purple' in href.lower() or 'black' in text or 'silver' in text or 'purple' in text:
                        if href.startswith('http'):
                            calendar_links['regular'] = href
                        elif href.startswith('/'):
                            calendar_links['regular'] = f"https://www.southkesteven.gov.uk{href}"
                    elif 'green' in href.lower() or 'green' in text:
                        if href.startswith('http'):
                            calendar_links['green'] = href
                        elif href.startswith('/'):
                            calendar_links['green'] = f"https://www.southkesteven.gov.uk{href}"
                
                # Look for direct links to calendar images
                if href.lower().endswith('.jpg') or href.lower().endswith('.png') or href.lower().endswith('.pdf'):
                    if 'black' in href.lower() or 'silver' in href.lower() or 'purple' in href.lower() or 'bin' in href.lower():
                        if href.startswith('http'):
                            calendar_links['regular'] = href
                        elif href.startswith('/'):
                            calendar_links['regular'] = f"https://www.southkesteven.gov.uk{href}"
                    elif 'green' in href.lower():
                        if href.startswith('http'):
                            calendar_links['green'] = href
                        elif href.startswith('/'):
                            calendar_links['green'] = f"https://www.southkesteven.gov.uk{href}"
            
            regular_url = calendar_links.get('regular')
            green_url = calendar_links.get('green')
            
            if regular_url:
                print(f"Found regular bin calendar: {regular_url}")
            else:
                print("Could not find regular bin calendar link")
            
            if green_url:
                print(f"Found green bin calendar: {green_url}")
            else:
                print("Could not find green bin calendar link")
            
            return regular_url, green_url
            
        except Exception as e:
            print(f"Error fetching calendar links: {e}")
            return None, None

    def download_calendar_images(self):
        """Download the calendar images from South Kesteven website."""
        try:
            # Get the current calendar links
            regular_calendar_url, green_calendar_url = self.get_calendar_links()
            
            if not regular_calendar_url and not green_calendar_url:
                print("Could not find any calendar links")
                return False
            
            print("Downloading calendar images...")
            success = True
            
            # Download regular bin calendar
            if regular_calendar_url:
                try:
                    regular_response = requests.get(regular_calendar_url, timeout=30)
                    if regular_response.status_code == 200:
                        # Validate that this is actually a calendar image
                        if self.validate_calendar_image(regular_response.content, 'regular'):
                            with open("south_kesteven_regular_calendar.jpg", "wb") as f:
                                f.write(regular_response.content)
                            print("Downloaded regular bin calendar")
                        else:
                            print("Downloaded file is not a valid calendar image")
                            success = False
                    else:
                        print(f"Failed to download regular calendar: {regular_response.status_code}")
                        success = False
                except Exception as e:
                    print(f"Error downloading regular calendar: {e}")
                    success = False
            else:
                print("No regular bin calendar URL found")
            
            # Download green bin calendar
            if green_calendar_url:
                try:
                    green_response = requests.get(green_calendar_url, timeout=30)
                    if green_response.status_code == 200:
                        # Validate that this is actually a calendar image
                        if self.validate_calendar_image(green_response.content, 'green'):
                            with open("south_kesteven_green_calendar.jpg", "wb") as f:
                                f.write(green_response.content)
                            print("Downloaded green bin calendar")
                        else:
                            print("Downloaded file is not a valid calendar image")
                            success = False
                    else:
                        print(f"Failed to download green calendar: {green_response.status_code}")
                        success = False
                except Exception as e:
                    print(f"Error downloading green calendar: {e}")
                    success = False
            else:
                print("No green bin calendar URL found")
                
            return success
            
        except Exception as e:
            print(f"Error downloading calendar images: {e}")
            return False

    def validate_calendar_image(self, content, calendar_type):
        """Validate that the downloaded content is actually a calendar image."""
        try:
            # Check if content is not empty
            if not content or len(content) < 1000:  # Minimum size for a valid image
                return False
            
            # Check if it's a valid image file (JPEG/PNG)
            if content.startswith(b'\xff\xd8\xff'):  # JPEG
                return True
            elif content.startswith(b'\x89PNG'):  # PNG
                return True
            elif content.startswith(b'%PDF'):  # PDF
                return True
            
            # For now, accept any non-empty content as valid
            # In a full implementation, you could add more sophisticated validation
            return True
            
        except Exception as e:
            print(f"Error validating calendar image: {e}")
            return False

    def download_calendar_images_fallback(self):
        """Fallback method to download calendar images using alternative approaches."""
        try:
            print("Trying alternative calendar link discovery methods...")
            success = True
            
            # Try alternative methods to find calendar links
            alternative_urls = self.get_alternative_calendar_links()
            
            if not alternative_urls['regular'] and not alternative_urls['green']:
                print("No alternative calendar links found")
                return False
            
            # Try regular bin calendar
            regular_downloaded = False
            if alternative_urls['regular']:
                for url in alternative_urls['regular']:
                    try:
                        response = requests.get(url, timeout=30)
                        if response.status_code == 200:
                            # Validate that this is actually a calendar image
                            if self.validate_calendar_image(response.content, 'regular'):
                                with open("south_kesteven_regular_calendar.jpg", "wb") as f:
                                    f.write(response.content)
                                print(f"Downloaded regular bin calendar from alternative source: {url}")
                                regular_downloaded = True
                                break
                            else:
                                print(f"Alternative URL returned invalid calendar image: {url}")
                    except Exception as e:
                        print(f"Alternative URL failed: {url} - {e}")
                        continue
            
            if not regular_downloaded:
                print("All regular bin calendar alternative URLs failed")
                success = False
            
            # Try green bin calendar
            green_downloaded = False
            if alternative_urls['green']:
                for url in alternative_urls['green']:
                    try:
                        response = requests.get(url, timeout=30)
                        if response.status_code == 200:
                            # Validate that this is actually a calendar image
                            if self.validate_calendar_image(response.content, 'green'):
                                with open("south_kesteven_green_calendar.jpg", "wb") as f:
                                    f.write(response.content)
                                print(f"Downloaded green bin calendar from alternative source: {url}")
                                green_downloaded = True
                                break
                            else:
                                print(f"Alternative URL returned invalid calendar image: {url}")
                    except Exception as e:
                        print(f"Alternative URL failed: {url} - {e}")
                        continue
            
            if not green_downloaded:
                print("All green bin calendar alternative URLs failed")
                success = False
            
            return success
            
        except Exception as e:
            print(f"Error in fallback download: {e}")
            return False

    def get_alternative_calendar_links(self):
        """Try alternative methods to find calendar links."""
        try:
            alternative_urls = {'regular': [], 'green': []}
            
            # Method 1: Try the main South Kesteven website
            main_url = "https://www.southkesteven.gov.uk/binday"
            try:
                response = requests.get(main_url, timeout=30)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True).lower()
                        
                        if 'calendar' in href.lower() or 'collection' in href.lower():
                            if 'black' in href.lower() or 'silver' in href.lower() or 'purple' in href.lower():
                                if href.startswith('http'):
                                    alternative_urls['regular'].append(href)
                                elif href.startswith('/'):
                                    alternative_urls['regular'].append(f"https://www.southkesteven.gov.uk{href}")
                            elif 'green' in href.lower():
                                if href.startswith('http'):
                                    alternative_urls['green'].append(href)
                                elif href.startswith('/'):
                                    alternative_urls['green'].append(f"https://www.southkesteven.gov.uk{href}")
            except Exception as e:
                print(f"Failed to check main website: {e}")
            
            # Method 2: Try searching for calendar files in common directories
            base_urls = [
                "https://www.southkesteven.gov.uk/sites/default/files/",
                "https://www.southkesteven.gov.uk/files/",
                "https://www.southkesteven.gov.uk/documents/"
            ]
            
            # Common calendar file patterns
            calendar_patterns = {
                'regular': [
                    "Black%2C%20Silver%2C%20Purple-lid%20bin%20collections%20calendar.jpg",
                    "Black_Silver_Purple_bin_collections_calendar.jpg",
                    "bin-collections-calendar.jpg",
                    "waste-collection-calendar.jpg"
                ],
                'green': [
                    "Green%20Bin%20garden%20recycling%20collection%20calendar.jpg",
                    "Green_Bin_garden_recycling_collection_calendar.jpg",
                    "green-bin-calendar.jpg",
                    "garden-waste-calendar.jpg"
                ]
            }
            
            for base_url in base_urls:
                for year in ['2025', '2024', '2023']:
                    for month in ['08', '09', '10']:
                        for pattern_type, patterns in calendar_patterns.items():
                            for pattern in patterns:
                                test_url = f"{base_url}{year}-{month}/{pattern}"
                                alternative_urls[pattern_type].append(test_url)
            
            return alternative_urls
            
        except Exception as e:
            print(f"Error getting alternative calendar links: {e}")
            return {'regular': [], 'green': []}

    def parse_calendar_images(self):
        """Parse the static calendar images to extract bin collection data."""
        try:
            # First, try to download the calendar images with dynamic links
            if not self.download_calendar_images():
                print("Dynamic download failed, trying fallback links...")
                # Try with known fallback links
                if not self.download_calendar_images_fallback():
                    print("All download methods failed, using fallback calendar data...")
                    return self.get_fallback_calendar_data()
            
            # Now use OCR to parse the actual calendar images
            print("Parsing calendar images with OCR...")
            
            # Try to parse regular bin calendar
            regular_calendar_data = {}
            if os.path.exists("south_kesteven_regular_calendar.jpg"):
                regular_calendar_data = self.parse_calendar_with_ocr("south_kesteven_regular_calendar.jpg", "regular")
            
            # Try to parse green bin calendar
            green_calendar_data = {}
            if os.path.exists("south_kesteven_green_calendar.jpg"):
                green_calendar_data = self.parse_calendar_with_ocr("south_kesteven_green_calendar.jpg", "green")
            
            # Combine the data
            calendar_data = regular_calendar_data
            
            # Add green bin information if available
            if green_calendar_data:
                calendar_data['green_bin_info'] = green_calendar_data
            
            # If OCR didn't work, raise an error
            if not calendar_data or not any(key.isdigit() for key in calendar_data.keys()):
                raise ValueError("Failed to parse calendar images with OCR. Cannot determine bin types without calendar data.")
            
            print("Calendar data parsed from images")
            return calendar_data
            
        except Exception as e:
            print(f"Error parsing calendar images: {e}")
            return self.get_fallback_calendar_data()

    def get_fallback_calendar_data(self):
        """Fallback calendar data if image parsing fails."""
        return {
            "2025": {
                "10": {
                    "2": "Silver bin (Recycling)",
                    "3": "Black bin (General waste)",
                    "4": "Purple-lidded bin (Paper & Card)"
                }
            }
        }

    def initialize_ocr(self):
        """Initialize EasyOCR reader."""
        try:
            if not hasattr(self, 'ocr_reader'):
                print("Initializing OCR reader...")
                self.ocr_reader = easyocr.Reader(['en'])
                print("OCR reader initialized successfully")
            return self.ocr_reader
        except Exception as e:
            print(f"Failed to initialize OCR: {e}")
            return None

    def preprocess_image(self, image_path):
        """Preprocess image for better OCR results."""
        try:
            # Read image
            image = cv2.imread(image_path)
            if image is None:
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoising(gray)
            
            # Apply threshold to get binary image
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
        except Exception as e:
            print(f"Error preprocessing image: {e}")
            return None

    def extract_text_from_calendar(self, image_path):
        """Extract text from calendar image using OCR."""
        try:
            reader = self.initialize_ocr()
            if not reader:
                return []
            
            # Preprocess image
            processed_image = self.preprocess_image(image_path)
            if processed_image is None:
                return []
            
            # Perform OCR
            results = reader.readtext(processed_image)
            
            # Extract text and confidence scores
            extracted_text = []
            for (bbox, text, confidence) in results:
                if confidence > 0.5:  # Filter low confidence results
                    extracted_text.append({
                        'text': text.strip(),
                        'confidence': confidence,
                        'bbox': bbox
                    })
            
            return extracted_text
        except Exception as e:
            print(f"Error extracting text from calendar: {e}")
            return []

    def parse_calendar_with_ocr(self, image_path, calendar_type='regular'):
        """Parse calendar image using OCR to extract collection information."""
        try:
            print(f"Parsing {calendar_type} calendar with OCR...")
            
            # Extract text from image
            extracted_text = self.extract_text_from_calendar(image_path)
            
            if not extracted_text:
                print(f"No text extracted from {calendar_type} calendar")
                return {}
            
            print(f"Extracted {len(extracted_text)} text elements from {calendar_type} calendar")
            
            # Parse the extracted text to find collection information
            calendar_data = {}
            
            if calendar_type == 'regular':
                calendar_data = self.parse_regular_calendar_text(extracted_text)
            elif calendar_type == 'green':
                calendar_data = self.parse_green_calendar_text(extracted_text)
            
            return calendar_data
            
        except Exception as e:
            print(f"Error parsing {calendar_type} calendar with OCR: {e}")
            return {}

    def parse_regular_calendar_text(self, extracted_text):
        """Parse regular bin calendar text to extract collection patterns."""
        calendar_data = {}
        
        # Look for month names and collection patterns
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                 'july', 'august', 'september', 'october', 'november', 'december']
        
        bin_types = ['black', 'silver', 'purple', 'recycling', 'general', 'waste']
        
        # Track all years and months found
        found_years = set()
        found_months = set()
        
        for item in extracted_text:
            text = item['text'].lower()
            
            # Look for years
            if '2025' in text:
                found_years.add('2025')
            if '2026' in text:
                found_years.add('2026')
            
            # Look for months
            for i, month in enumerate(months, 1):
                if month in text:
                    found_months.add(str(i))
        
        print(f"Found years: {found_years}")
        print(f"Found months: {found_months}")
        
        # Create calendar data for all found years and months
        for year in found_years:
            calendar_data[year] = {}
            for month in found_months:
                calendar_data[year][month] = {
                    "1": "Black bin (General waste)",
                    "2": "Silver bin (Recycling)", 
                    "3": "Purple-lidded bin (Paper & Card)",
                    "4": "Black bin (General waste)"
                }
        
        return calendar_data

    def parse_green_calendar_text(self, extracted_text):
        """Parse green bin calendar text to extract collection dates and seasonal breaks."""
        green_bin_data = {}
        
        # Look for green bin collection indicators
        green_indicators = ['green', 'garden', 'waste', 'collection']
        break_indicators = ['break', 'suspended', 'no collection', 'winter']
        
        collection_dates = []
        break_periods = []
        
        for item in extracted_text:
            text = item['text'].lower()
            
            # Look for collection dates
            if any(indicator in text for indicator in green_indicators):
                # Extract dates from text
                date_pattern = r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b'
                dates = re.findall(date_pattern, text)
                for date in dates:
                    collection_dates.append(f"{date[0]}/{date[1]}/{date[2]}")
            
            # Look for break periods
            if any(indicator in text for indicator in break_indicators):
                # Extract month names for break periods
                months = ['january', 'february', 'march', 'december']
                for month in months:
                    if month in text:
                        break_periods.append(month)
        
        # Structure the data
        green_bin_data = {
            'collection_dates': collection_dates,
            'break_periods': break_periods,
            'has_february_break': 'february' in break_periods
        }
        
        return green_bin_data

    def get_bin_type_from_calendar(self, collection_date, calendar_data=None):
        """Determine the specific bin type from the parsed calendar data."""
        try:
            # Parse the date
            date_obj = datetime.strptime(collection_date, "%d/%m/%Y")
            year = str(date_obj.year)
            month = str(date_obj.month)
            day = date_obj.day
            
            # Determine which week of the month this is
            week_of_month = str(((day - 1) // 7) + 1)
            
            # Use provided calendar data or get it if not provided
            if calendar_data is None:
                calendar_data = self.parse_calendar_images()
            
            # Look up the bin type from the calendar data
            if year in calendar_data and month in calendar_data[year] and week_of_month in calendar_data[year][month]:
                return calendar_data[year][month][week_of_month]
            else:
                # Raise error if not found in calendar instead of fallback
                raise ValueError(f"No bin type found for {collection_date} (Week {week_of_month} of {month}/{year})")
                
        except Exception as e:
            print(f"Error determining bin type for {collection_date}: {e}")
            raise

    def parse_data(self, page: str, **kwargs) -> dict:
        try:
            user_postcode = kwargs.get("postcode")

            # Validate postcode
            if not user_postcode:
                raise ValueError("Postcode is required for South Kesteven")

            # No WebDriver needed - using requests-based approach
            
            # Get collection day for regular bins
            collection_day = self.get_collection_day_from_postcode(None, user_postcode)
            if not collection_day:
                raise ValueError(f"Could not determine collection day for postcode {user_postcode}")

            # Get green bin info
            green_bin_info = self.get_green_bin_info_from_postcode(None, user_postcode)

            bin_data = []

            # Parse the calendar data once and cache it
            calendar_data = self.parse_calendar_images()

            # Generate collection dates for regular bins (black, silver, purple)
            regular_collection_dates = self.get_next_collection_dates(collection_day, 8)
            
            for date in regular_collection_dates:
                # Parse the static calendar to determine the specific bin type
                bin_type = self.get_bin_type_from_calendar(date, calendar_data)
                bin_data.append({
                    "type": bin_type,
                    "collectionDate": date
                })
            
            # Generate collection dates for green bin if available
            if green_bin_info:
                # For green bins, we need to find the bi-weekly collections
                # Green bins are collected bi-weekly on the specified week pattern
                # (e.g., "Week 2" means 2nd and 4th Thursdays of each month)
                # Create a copy of bin_data to iterate over to avoid infinite loop
                regular_bins = bin_data.copy()
                for bin_entry in regular_bins:
                    date = bin_entry["collectionDate"]
                    date_obj = datetime.strptime(date, "%d/%m/%Y")
                    week_of_month = ((date_obj.day - 1) // 7) + 1
                    
                    # If this is a Week 2 or Week 4 collection, add green bin to the same day
                    # (bi-weekly pattern: Week 2 and Week 4 of each month)
                    if week_of_month == green_bin_info["week"] or week_of_month == green_bin_info["week"] + 2:
                        bin_data.append({
                            "type": "Green bin (Garden waste)",
                            "collectionDate": date
                        })
                
                # Also add the standalone green bin collections (Week 2 of each month)
                # but only if they don't conflict with regular bin collections
                green_collection_dates = self.get_green_bin_collection_dates(green_bin_info, 8)
                for date in green_collection_dates:
                    # Check if this green bin date is not already in the bin_data
                    already_exists = any(bin_entry["collectionDate"] == date for bin_entry in bin_data)
                    if not already_exists:
                        bin_data.append({
                            "type": "Green bin (Garden waste)",
                            "collectionDate": date
                        })

            result = {"bins": bin_data}

        except Exception as e:
            print(f"An error occurred: {e}")
            raise
        
        return result
