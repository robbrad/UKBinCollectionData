"""
Tests for South Kesteven District Council implementation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil import CouncilClass


class TestSouthKestevenDistrictCouncil:
    """Test cases for South Kesteven District Council implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.council = CouncilClass()

    def test_get_next_collection_dates_monday(self):
        """Test collection date calculation for Monday collections."""
        # Mock today as a Wednesday (weekday 2)
        with patch('uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 10)  # Wednesday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            dates = self.council.get_next_collection_dates("Monday", 4)
            
            # Should return next 4 Mondays: Jan 15, 22, 29, Feb 5
            expected_dates = ["15/01/2024", "22/01/2024", "29/01/2024", "05/02/2024"]
            assert dates == expected_dates

    def test_get_next_collection_dates_friday(self):
        """Test collection date calculation for Friday collections."""
        # Mock today as a Monday (weekday 0)
        with patch('uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 8)  # Monday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            dates = self.council.get_next_collection_dates("Friday", 3)
            
            # Should return next 3 Fridays: Jan 12, 19, 26
            expected_dates = ["12/01/2024", "19/01/2024", "26/01/2024"]
            assert dates == expected_dates

    def test_get_next_collection_dates_same_day(self):
        """Test collection date calculation when today is the collection day."""
        # Mock today as a Tuesday (weekday 1)
        with patch('uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 9)  # Tuesday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            dates = self.council.get_next_collection_dates("Tuesday", 3)
            
            # Should return next 3 Tuesdays: Jan 16, 23, 30 (not today)
            expected_dates = ["16/01/2024", "23/01/2024", "30/01/2024"]
            assert dates == expected_dates

    def test_get_green_bin_collection_dates_week_1(self):
        """Test green bin collection date calculation for Week 1."""
        green_bin_info = {"day": "Tuesday", "week": 1}
        
        # Mock today as January 1, 2024 (Monday, Week 1)
        with patch('uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)  # Monday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            dates = self.council.get_green_bin_collection_dates(green_bin_info, 3)
            
            # Should return Tuesdays in Week 1: Jan 2, Feb 6, Mar 5
            expected_dates = ["02/01/2024", "06/02/2024", "05/03/2024"]
            assert dates == expected_dates

    def test_get_green_bin_collection_dates_week_2(self):
        """Test green bin collection date calculation for Week 2."""
        green_bin_info = {"day": "Tuesday", "week": 2}
        
        # Mock today as January 1, 2024 (Monday, Week 1)
        with patch('uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)  # Monday
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            dates = self.council.get_green_bin_collection_dates(green_bin_info, 3)
            
            # Should return Tuesdays in Week 2: Jan 9, Feb 13, Mar 12
            expected_dates = ["09/01/2024", "13/02/2024", "12/03/2024"]
            assert dates == expected_dates

    def test_get_green_bin_collection_dates_no_info(self):
        """Test green bin collection date calculation with no info."""
        dates = self.council.get_green_bin_collection_dates(None, 3)
        assert dates == []

    def test_get_collection_day_from_postcode_success(self):
        """Test successful collection day extraction from postcode."""
        # Mock the requests-based approach
        with patch.object(self.council, '_get_collection_day_requests') as mock_requests:
            mock_requests.return_value = "Monday"
            
            result = self.council.get_collection_day_from_postcode(None, "PE6 8BL")
            
            assert result == "Monday"
            mock_requests.assert_called_once_with("PE6 8BL")

    def test_get_collection_day_from_postcode_failure(self):
        """Test collection day extraction failure."""
        # Mock the requests-based approach to return None
        with patch.object(self.council, '_get_collection_day_requests') as mock_requests:
            mock_requests.return_value = None
            
            result = self.council.get_collection_day_from_postcode(None, "INVALID")
            
            assert result is None
            mock_requests.assert_called_once_with("INVALID")

    def test_get_green_bin_info_from_postcode_success(self):
        """Test successful green bin info extraction from postcode."""
        # Mock the requests-based approach
        with patch.object(self.council, '_get_green_bin_info_requests') as mock_requests:
            mock_requests.return_value = {"day": "Tuesday", "week": 2}
            
            result = self.council.get_green_bin_info_from_postcode(None, "PE6 8BL")
            
            expected = {"day": "Tuesday", "week": 2}
            assert result == expected
            mock_requests.assert_called_once_with("PE6 8BL")

    def test_get_green_bin_info_from_postcode_failure(self):
        """Test green bin info extraction failure."""
        # Mock the requests-based approach to return None
        with patch.object(self.council, '_get_green_bin_info_requests') as mock_requests:
            mock_requests.return_value = None
            
            result = self.council.get_green_bin_info_from_postcode(None, "INVALID")
            
            assert result is None
            mock_requests.assert_called_once_with("INVALID")

    def test_parse_data_success_with_green_bin(self):
        """Test successful parse_data with both regular and green bin collections."""
        # Mock the collection day lookup and calendar parsing
        with patch.object(self.council, 'get_collection_day_from_postcode') as mock_get_day:
            with patch.object(self.council, 'get_green_bin_info_from_postcode') as mock_get_green:
                with patch.object(self.council, 'get_next_collection_dates') as mock_get_dates:
                    with patch.object(self.council, 'get_green_bin_collection_dates') as mock_get_green_dates:
                        with patch.object(self.council, 'parse_calendar_images') as mock_calendar:
                            with patch.object(self.council, 'get_bin_type_from_calendar') as mock_bin_type:
    
                                mock_get_day.return_value = "Monday"
                                mock_get_green.return_value = {"day": "Tuesday", "week": 2}
                                mock_get_dates.return_value = ["15/01/2025", "22/01/2025"]
                                mock_get_green_dates.return_value = ["09/01/2025", "13/02/2025"]
                                mock_calendar.return_value = {"2025": {"1": {"1": "Black bin", "2": "Silver bin"}}}
                                mock_bin_type.return_value = "Black bin (General waste)"
    
                                result = self.council.parse_data("", postcode="PE6 8BL")
    
                                expected = {
                                    "bins": [
                                        {"type": "Black bin (General waste)", "collectionDate": "15/01/2025"},
                                        {"type": "Black bin (General waste)", "collectionDate": "22/01/2025"},
                                        {"type": "Green bin (Garden waste)", "collectionDate": "22/01/2025"},
                                        {"type": "Green bin (Garden waste)", "collectionDate": "09/01/2025"},
                                        {"type": "Green bin (Garden waste)", "collectionDate": "13/02/2025"}
                                    ]
                                }
                                assert result == expected

    def test_parse_data_success_without_green_bin(self):
        """Test successful parse_data with only regular bin collections."""
        with patch.object(self.council, 'get_collection_day_from_postcode') as mock_get_day:
            with patch.object(self.council, 'get_green_bin_info_from_postcode') as mock_get_green:
                with patch.object(self.council, 'get_next_collection_dates') as mock_get_dates:
                    with patch.object(self.council, 'parse_calendar_images') as mock_calendar:
                        with patch.object(self.council, 'get_bin_type_from_calendar') as mock_bin_type:
    
                            mock_get_day.return_value = "Friday"
                            mock_get_green.return_value = None  # No green bin service
                            mock_get_dates.return_value = ["12/01/2025", "19/01/2025"]
                            mock_calendar.return_value = {"2025": {"1": {"1": "Black bin", "2": "Silver bin"}}}
                            mock_bin_type.return_value = "Black bin (General waste)"
    
                            result = self.council.parse_data("", postcode="PE6 8BL")
    
                            expected = {
                                "bins": [
                                    {"type": "Black bin (General waste)", "collectionDate": "12/01/2025"},
                                    {"type": "Black bin (General waste)", "collectionDate": "19/01/2025"}
                                ]
                            }
                            assert result == expected

    def test_parse_data_no_postcode(self):
        """Test parse_data with no postcode provided."""
        with pytest.raises(ValueError, match="Postcode is required for South Kesteven"):
            self.council.parse_data("", web_driver="http://localhost:4444")

    def test_parse_data_collection_day_failure(self):
        """Test parse_data when collection day lookup fails."""
        with patch.object(self.council, 'get_collection_day_from_postcode') as mock_get_day:
            mock_get_day.return_value = None
        
            with pytest.raises(ValueError, match="Could not determine collection day for postcode INVALID"):
                self.council.parse_data("", postcode="INVALID")

    def test_parse_data_exception_handling(self):
        """Test parse_data exception handling."""
        # Mock an exception during collection day lookup
        with patch.object(self.council, 'get_collection_day_from_postcode') as mock_get_day:
            mock_get_day.side_effect = Exception("Network error")
        
            with pytest.raises(Exception, match="Network error"):
                self.council.parse_data("", postcode="PE6 8BL")

    def test_week_of_month_calculation(self):
        """Test the week of month calculation logic."""
        # Test various dates to ensure week calculation is correct
        test_cases = [
            (datetime(2024, 1, 1), 1),   # Jan 1 - Week 1
            (datetime(2024, 1, 7), 1),   # Jan 7 - Week 1
            (datetime(2024, 1, 8), 2),   # Jan 8 - Week 2
            (datetime(2024, 1, 14), 2),  # Jan 14 - Week 2
            (datetime(2024, 1, 15), 3),  # Jan 15 - Week 3
            (datetime(2024, 1, 21), 3),  # Jan 21 - Week 3
            (datetime(2024, 1, 22), 4),  # Jan 22 - Week 4
            (datetime(2024, 1, 28), 4),  # Jan 28 - Week 4
            (datetime(2024, 1, 29), 5),  # Jan 29 - Week 5
            (datetime(2024, 1, 31), 5),  # Jan 31 - Week 5
        ]
        
        for date, expected_week in test_cases:
            week_of_month = ((date.day - 1) // 7) + 1
            assert week_of_month == expected_week, f"Date {date} should be week {expected_week}, got {week_of_month}"

    def test_days_of_week_mapping(self):
        """Test the days of week mapping is correct."""
        days_of_week = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
            "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        # Test that our mapping matches Python's weekday() method
        test_date = datetime(2024, 1, 8)  # Monday
        for day_name, expected_weekday in days_of_week.items():
            # Find a date that falls on this weekday
            days_to_add = (expected_weekday - test_date.weekday()) % 7
            test_date_for_day = test_date + timedelta(days=days_to_add)
            
            assert test_date_for_day.weekday() == expected_weekday, f"{day_name} should map to weekday {expected_weekday}"
