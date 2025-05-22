#!/usr/bin/env python3
"""
Script to convert UK Bin Collection Data to ICS calendar file.
Takes JSON output from the bin collection data retriever and creates calendar events
for each collection date. The events are saved to an ICS file that can be imported
into calendar applications.

Features:
- Creates all-day events for bin collections by default
- Optional alarms/reminders before collection days
- Groups multiple bin collections on the same day into one event
"""

import argparse
import datetime
import json
import os
import sys
from typing import Dict, List, Optional, Union

try:
    from icalendar import Calendar, Event, Alarm
except ImportError:
    print("Error: Required package 'icalendar' not found.")
    print("Please install it with: pip install icalendar")
    sys.exit(1)


def parse_time_delta(time_str: str) -> datetime.timedelta:
    """
    Parse a time string into a timedelta object.
    
    Formats supported:
    - "1d" or "1day" or "1days" for days
    - "2h" or "2hour" or "2hours" for hours
    - "30m" or "30min" or "30mins" or "30minutes" for minutes
    
    Args:
        time_str: String representing a time duration
        
    Returns:
        timedelta object representing the duration
    """
    time_str = time_str.lower().strip()
    
    # Handle days
    if time_str.endswith('d') or time_str.endswith('day') or time_str.endswith('days'):
        if time_str.endswith('days'):
            value = int(time_str[:-4])
        elif time_str.endswith('day'):
            value = int(time_str[:-3])
        else:
            value = int(time_str[:-1])
        return datetime.timedelta(days=value)
    
    # Handle hours
    elif time_str.endswith('h') or time_str.endswith('hour') or time_str.endswith('hours'):
        if time_str.endswith('hours'):
            value = int(time_str[:-5])
        elif time_str.endswith('hour'):
            value = int(time_str[:-4])
        else:
            value = int(time_str[:-1])
        return datetime.timedelta(hours=value)
    
    # Handle minutes
    elif time_str.endswith('m') or time_str.endswith('min') or time_str.endswith('mins') or time_str.endswith('minutes'):
        if time_str.endswith('minutes'):
            value = int(time_str[:-7])
        elif time_str.endswith('mins'):
            value = int(time_str[:-4])
        elif time_str.endswith('min'):
            value = int(time_str[:-3])
        else:
            value = int(time_str[:-1])
        return datetime.timedelta(minutes=value)
    
    # Default to hours if no unit specified
    else:
        try:
            value = int(time_str)
            return datetime.timedelta(hours=value)
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}. Use format like '1d', '2h', or '30m'.")


def create_bin_calendar(
    bin_data: Dict,
    calendar_name: str = "Bin Collections",
    alarm_times: Optional[List[datetime.timedelta]] = None,
    all_day: bool = True
) -> Calendar:
    """
    Create a calendar from bin collection data.
    
    Args:
        bin_data: Dictionary containing bin collection data
        calendar_name: Name of the calendar
        alarm_times: List of timedeltas for when reminders should trigger before the event
        all_day: Whether the events should be all-day events
        
    Returns:
        Calendar object with events for each bin collection
    """
    cal = Calendar()
    cal.add('prodid', '-//UK Bin Collection Data//bin_to_ics.py//EN')
    cal.add('version', '2.0')
    cal.add('name', calendar_name)
    cal.add('x-wr-calname', calendar_name)
    
    # Process bin collection data
    if 'bins' not in bin_data:
        print("Error: Invalid bin data format. 'bins' key not found.")
        sys.exit(1)
    
    # Group collections by date to combine bins collected on the same day
    collections_by_date = {}
    
    for bin_info in bin_data['bins']:
        if 'type' not in bin_info or 'collectionDate' not in bin_info:
            continue
        
        bin_type = bin_info['type']
        collection_date_str = bin_info['collectionDate']
        
        # Convert date string to datetime object
        try:
            # Expecting format DD/MM/YYYY
            collection_date = datetime.datetime.strptime(collection_date_str, "%d/%m/%Y").date()
        except ValueError:
            print(f"Warning: Unable to parse date '{collection_date_str}'. Skipping.")
            continue
        
        # Add to collections by date
        if collection_date not in collections_by_date:
            collections_by_date[collection_date] = []
        
        collections_by_date[collection_date].append(bin_type)
    
    # Create events for each collection date
    for collection_date, bin_types in collections_by_date.items():
        event = Event()
        
        # Join multiple bin types into one summary if needed
        bin_types_str = ", ".join(bin_types)
        
        # Create event summary and description
        summary = f"Bin Collection: {bin_types_str}"
        description = f"Collection for: {bin_types_str}"
        
        # Add event details
        event.add('summary', summary)
        event.add('description', description)
        
        # Set the event as all-day if requested
        if all_day:
            event.add('dtstart', collection_date)
            event.add('dtend', collection_date + datetime.timedelta(days=1))
        else:
            # Default to 7am for non-all-day events
            collection_datetime = datetime.datetime.combine(
                collection_date, 
                datetime.time(7, 0, 0)
            )
            event.add('dtstart', collection_datetime)
            event.add('dtend', collection_datetime + datetime.timedelta(hours=1))
        
        # Add alarms if specified
        if alarm_times:
            for alarm_time in alarm_times:
                alarm = create_alarm(trigger_before=alarm_time)
                event.add_component(alarm)
        
        # Generate a unique ID for the event
        event_id = f"bin-collection-{collection_date.isoformat()}-{hash(bin_types_str) % 10000:04d}@ukbincollection"
        event.add('uid', event_id)
        
        # Add the event to the calendar
        cal.add_component(event)
    
    return cal


def create_alarm(trigger_before: datetime.timedelta) -> Alarm:
    """
    Create an alarm component for calendar events.
    
    Args:
        trigger_before: How long before the event to trigger the alarm
        
    Returns:
        Alarm component
    """
    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('description', 'Bin collection reminder')
    alarm.add('trigger', -trigger_before)
    
    return alarm


def save_calendar(calendar: Calendar, output_file: str) -> None:
    """
    Save a calendar to an ICS file.
    
    Args:
        calendar: Calendar object to save
        output_file: Path to save the calendar file
    """
    with open(output_file, 'wb') as f:
        f.write(calendar.to_ical())
    
    print(f"Calendar saved to {output_file}")


def load_json_data(input_file: Optional[str] = None) -> Dict:
    """
    Load bin collection data from JSON file or stdin.
    
    Args:
        input_file: Path to JSON file (if None, read from stdin)
        
    Returns:
        Dictionary containing bin collection data
    """
    if input_file:
        try:
            with open(input_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error reading input file: {e}")
            sys.exit(1)
    else:
        try:
            return json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from stdin: {e}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Convert UK Bin Collection Data to ICS calendar file.')
    parser.add_argument('--input', '-i', help='Input JSON file (if not provided, read from stdin)')
    parser.add_argument('--output', '-o', help='Output ICS file (default: bin.ics)', 
                       default='bin.ics')
    parser.add_argument('--name', '-n', help='Calendar name (default: Bin Collections)',
                       default='Bin Collections')
    parser.add_argument('--alarms', '-a', help='Comma-separated list of alarm times before event (e.g., "1d,2h,30m")')
    parser.add_argument('--no-all-day', action='store_true', help='Create timed events instead of all-day events')
    
    args = parser.parse_args()
    
    # Parse alarm times
    alarm_times = None
    if args.alarms:
        alarm_times = []
        for alarm_str in args.alarms.split(','):
            try:
                alarm_times.append(parse_time_delta(alarm_str.strip()))
            except ValueError as e:
                print(f"Warning: {e}")
    
    # Load bin collection data
    bin_data = load_json_data(args.input)
    
    # Create calendar
    calendar = create_bin_calendar(
        bin_data, 
        args.name, 
        alarm_times=alarm_times,
        all_day=not args.no_all_day
    )
    
    # Save calendar to file
    save_calendar(calendar, args.output)


if __name__ == '__main__':
    main()

