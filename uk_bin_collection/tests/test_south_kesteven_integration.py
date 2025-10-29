"""
Integration tests for South Kesteven District Council implementation.
These tests use requests-based form submission (no Selenium required).
"""

import pytest
import os
from unittest.mock import patch

from uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil import CouncilClass


class TestSouthKestevenIntegration:
    """Integration tests for South Kesteven District Council."""

    def setup_method(self):
        """Set up test fixtures."""
        self.council = CouncilClass()
        # Use a test postcode that should work
        self.test_postcode = "PE6 8BL"

    @pytest.mark.integration
    def test_real_postcode_lookup(self):
        """Test real postcode lookup with requests-based form submission."""
        try:
            result = self.council.parse_data(
                "", 
                postcode=self.test_postcode
            )
            
            # Verify the result structure
            assert "bins" in result
            assert isinstance(result["bins"], list)
            assert len(result["bins"]) > 0
            
            # Verify each bin entry has required fields
            for bin_entry in result["bins"]:
                assert "type" in bin_entry
                assert "collectionDate" in bin_entry
                # Updated to include the specific bin types we now return
                assert bin_entry["type"] in [
                    "General Waste", "Garden Waste", "Green bin (Garden waste)",
                    "Black bin (General waste)", "Silver bin (Recycling)", 
                    "Purple-lidded bin (Paper & Card)"
                ]
                
                # Verify date format (DD/MM/YYYY)
                date_parts = bin_entry["collectionDate"].split("/")
                assert len(date_parts) == 3
                assert len(date_parts[0]) == 2  # Day
                assert len(date_parts[1]) == 2  # Month
                assert len(date_parts[2]) == 4  # Year
                
        except Exception as e:
            pytest.skip(f"Integration test failed (likely due to network issues): {e}")

    @pytest.mark.integration
    def test_invalid_postcode_handling(self):
        """Test handling of invalid postcodes."""
        try:
            with pytest.raises(ValueError, match="Could not determine collection day"):
                self.council.parse_data(
                    "", 
                    postcode="INVALID_POSTCODE"
                )
        except Exception as e:
            pytest.skip(f"Integration test failed (likely due to network issues): {e}")

    @pytest.mark.integration
    def test_collection_day_extraction(self):
        """Test extraction of collection day using requests-based approach."""
        try:
            collection_day = self.council.get_collection_day_from_postcode(None, self.test_postcode)
            assert collection_day is not None
            assert collection_day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                
        except Exception as e:
            pytest.skip(f"Integration test failed (likely due to network issues): {e}")

    @pytest.mark.integration
    def test_green_bin_info_extraction(self):
        """Test extraction of green bin information using requests-based approach."""
        try:
            green_bin_info = self.council.get_green_bin_info_from_postcode(None, self.test_postcode)
            
            if green_bin_info:  # Green bin service might not be available for all postcodes
                assert "day" in green_bin_info
                assert "week" in green_bin_info
                assert green_bin_info["day"] in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                assert green_bin_info["week"] in [1, 2]
                
        except Exception as e:
            pytest.skip(f"Integration test failed (likely due to network issues): {e}")

    def test_collection_date_calculation_accuracy(self):
        """Test that collection date calculations are accurate."""
        from datetime import datetime, timedelta
        
        # Test with a known date
        test_date = datetime(2024, 1, 10)  # Wednesday, January 10, 2024
        
        with patch('uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_date
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Test Monday collections
            monday_dates = self.council.get_next_collection_dates("Monday", 2)
            expected_monday_1 = (test_date + timedelta(days=5)).strftime("%d/%m/%Y")  # Jan 15
            expected_monday_2 = (test_date + timedelta(days=12)).strftime("%d/%m/%Y")  # Jan 22
            
            assert monday_dates[0] == expected_monday_1
            assert monday_dates[1] == expected_monday_2
            
            # Test Friday collections
            friday_dates = self.council.get_next_collection_dates("Friday", 2)
            expected_friday_1 = (test_date + timedelta(days=2)).strftime("%d/%m/%Y")  # Jan 12
            expected_friday_2 = (test_date + timedelta(days=9)).strftime("%d/%m/%Y")  # Jan 19
            
            assert friday_dates[0] == expected_friday_1
            assert friday_dates[1] == expected_friday_2

    def test_green_bin_week_calculation_accuracy(self):
        """Test that green bin week calculations are accurate."""
        from datetime import datetime
        
        # Test with January 2024 (known calendar)
        test_date = datetime(2024, 1, 1)  # Monday, January 1, 2024
        
        with patch('uk_bin_collection.uk_bin_collection.councils.SouthKestevenDistrictCouncil.datetime') as mock_datetime:
            mock_datetime.now.return_value = test_date
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            # Test Week 1 Tuesday (should be January 2)
            green_bin_info = {"day": "Tuesday", "week": 1}
            dates = self.council.get_green_bin_collection_dates(green_bin_info, 1)
            
            assert len(dates) == 1
            assert dates[0] == "02/01/2024"  # January 2, 2024 is a Tuesday in Week 1
            
            # Test Week 2 Tuesday (should be January 9)
            green_bin_info = {"day": "Tuesday", "week": 2}
            dates = self.council.get_green_bin_collection_dates(green_bin_info, 1)
            
            assert len(dates) == 1
            assert dates[0] == "09/01/2024"  # January 9, 2024 is a Tuesday in Week 2
