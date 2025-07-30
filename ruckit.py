#!/usr/bin/env python3
"""
Scheduler to sync location data between Geotab and Ruckit APIs
Runs every 2 minutes to check for location discrepancies
"""

import time
import threading
import requests
import json
import mygeotab
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os
from dotenv import load_dotenv

class LocationSyncScheduler:
    def __init__(self, geotab_username: str, geotab_database: str, geotab_password: str):
        """
        Initialize the scheduler with Geotab credentials
        
        Args:
            geotab_username: Geotab username
            geotab_database: Geotab database name
            geotab_password: Geotab password
        """
        self.geotab_username = geotab_username
        self.geotab_database = geotab_database
        self.geotab_password = geotab_password
        self.geotab_api = None
        self.running = False
        self.scheduler_thread = None
        
        # Ruckit API endpoints
        self.URL_UPDATES = 'https://ruckit-platform.herokuapp.com/api/locationupdates/'
    
    def authenticate_geotab(self):
        """Authenticate with the MyGeotab API"""
        try:
            self.geotab_api = mygeotab.API(
                username=self.geotab_username, 
                password=self.geotab_password, 
                database=self.geotab_database
            )
            self.geotab_api.authenticate()
            print(f"Authenticated with Geotab successfully for database: {self.geotab_database}")
            return True
        except Exception as e:
            print(f"Failed to authenticate with Geotab: {e}")
            return False
    
    def get_geotab_data(self, type_name: str, **kwargs):
        """Wrapper for Geotab API calls"""
        try:
            print(f"Calling Geotab API for type: {type_name}")
            return self.geotab_api.call("Get", typeName=type_name, **kwargs)
        except Exception as e:
            print(f"Error calling Geotab API for {type_name}: {e}")
            return None
    
    def get_device_status_info(self) -> List[Dict]:
        """Get device status information from Geotab"""
        return self.get_geotab_data("DeviceStatusInfo") or []
    
    def get_add_in_data(self) -> List[Dict]:
        """Get AddInData from Geotab containing Ruckit mapping info"""
        search_params = {
            'whereClause': 'type = "ri-device"'
        }
        return self.get_geotab_data("AddInData", search=search_params) or []
    
    def get_ruckit_location_updates(self, ri_token: str, ri_driver: str) -> Optional[Dict]:
        """
        Get last location updates for a driver from Ruckit API
        
        Args:
            ri_token: Ruckit API token
            ri_driver: Ruckit driver ID
        
        Returns:
            Response JSON or None if failed
        """
        print(f"Fetching Ruckit location updates for driver {ri_driver} with token {ri_token}")
        headers = {
            'Authorization': f'Token {ri_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.URL_UPDATES}?driver={ri_driver}"
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ruckit API returned status {response.status_code} for driver {ri_driver}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Ruckit API request failed for driver {ri_driver}: {e}")
            return None
    
    def extract_coordinates(self, location_data: Dict) -> Optional[Tuple[float, float]]:
        """
        Extract coordinates from location data
        
        Args:
            location_data: Location object from API response
            
        Returns:
            Tuple of (longitude, latitude) or None if not found
        """
        try:
            if 'coordinates' in location_data:
                coords = location_data['coordinates']
                if len(coords) >= 2:
                    return (coords[0], coords[1])  # longitude, latitude
        except (KeyError, IndexError, TypeError):
            pass
        return None
    
    def coordinates_match(self, coord1: Tuple[float, float], coord2: Tuple[float, float], tolerance: float = 0.0001) -> bool:
        """
        Check if two coordinate pairs match within tolerance
        
        Args:
            coord1: First coordinate pair (longitude, latitude)
            coord2: Second coordinate pair (longitude, latitude)
            tolerance: Tolerance for coordinate comparison
            
        Returns:
            True if coordinates match within tolerance
        """
        if not coord1 or not coord2:
            return False
        
        lon_diff = abs(coord1[0] - coord2[0])
        lat_diff = abs(coord1[1] - coord2[1])
        
        return lon_diff <= tolerance and lat_diff <= tolerance
    
    def post_location_update_to_ruckit(self, ri_token: str, ri_device: str, ri_driver: str, device_id: str, geotab_location_data: Dict):
        """
        Post location update to Ruckit API using Geotab coordinates
        
        Args:
            ri_token: Ruckit API token
            ri_device: Ruckit device ID  
            ri_driver: Ruckit driver ID
            device_id: Geotab device ID
            geotab_location_data: Geotab location data containing latitude and longitude
        """
        headers = {
            'Authorization': f'Token {ri_token}',
            'Content-Type': 'application/json'
        }
        
        # Extract coordinates from Geotab location data
        geotab_lat = geotab_location_data.get('latitude')
        geotab_lon = geotab_location_data.get('longitude') 
        
        if geotab_lat is None or geotab_lon is None:
            print(f"Missing coordinates in Geotab data for device {device_id}")
            return None
        
        payload = json.dumps({
            'truck': ri_device,
            'driver': ri_driver,
            'device_id': device_id,
            'date': datetime.now().isoformat(),
            'location': {
                'type': 'Point',
                'coordinates': [geotab_lon, geotab_lat]  # Using Geotab coordinates
            },
            'orientation': 0.0,
            'speed': 0.0,
            'assignment': None,
            'jobevent': None,
            'provider': None,
            'accuracy': None
        })
        
        print(f"Payload to send to Ruckit: {payload}")
        
        try:
            response = requests.post(self.URL_UPDATES, headers=headers, data=payload)
            print(f"POST to Ruckit: {response.status_code} for device {ri_device}")
            if response.status_code in [200, 201]:
                print(f"Successfully posted location update for device {ri_device}")
                return response.json()
            else:
                print(f"Ruckit API error response: {response.text}")
                return None
        except Exception as e:
            print(f"Error posting to Ruckit for device {ri_device}: {e}")
            return None
            
    def is_placeholder_value(self, value: str) -> bool:
        """
        Check if a value is a placeholder that should be skipped
        
        Args:
            value: The value to check
            
        Returns:
            True if the value is a placeholder
        """
        if not isinstance(value, str):
            return False
        
        placeholder_values = {'TOKEN', 'DriverID', 'DeviceID'}
        return value in placeholder_values
    
    def process_location_sync(self):
        """Main processing function to sync locations between Geotab and Ruckit"""
        print(f"\n=== Starting location sync process at {datetime.now()} ===")
        
        try:
            # Get device status info from Geotab
            device_status_list = self.get_device_status_info()
            print(f"Retrieved {len(device_status_list)} device status records from Geotab")
            
            # Get AddInData from Geotab (contains Ruckit mapping)
            add_in_data_list = self.get_add_in_data()
            print(f"Retrieved {len(add_in_data_list)} AddInData records from Geotab")
            
            # Create mapping from gt-device to Ruckit info
            device_mapping = {}
            skipped_records = 0
            
            for add_in_data in add_in_data_list:
                try:
                    # Extract data from the details object
                    details = add_in_data.get('details', {})
                    
                    gt_device = details.get('gt-device')  # Device reference from details
                    ri_device = details.get('ri-device')
                    ri_token = details.get('ri-token')
                    ri_driver = details.get('ri-driver')
                    
                    # Check if all required fields are present
                    if not all([gt_device, ri_device, ri_token, ri_driver]):
                        print(f"Incomplete AddInData record - gt_device: {gt_device}, ri_device: {ri_device}, ri_token present: {bool(ri_token)}, ri_driver: {ri_driver}")
                        continue
                    
                    # Check if any values are placeholders
                    if (self.is_placeholder_value(ri_token) or 
                        self.is_placeholder_value(ri_driver) or 
                        self.is_placeholder_value(ri_device)):
                        print(f"Skipping AddInData record with placeholder values - gt_device: {gt_device}, ri_device: {ri_device}, ri_token: {ri_token}, ri_driver: {ri_driver}")
                        skipped_records += 1
                        continue
                    
                    device_mapping[gt_device] = {
                        'ri_device': ri_device,
                        'ri_token': ri_token,
                        'ri_driver': ri_driver
                    }
                    print(f"Mapped device {gt_device} to Ruckit driver {ri_driver}")
                        
                except Exception as e:
                    print(f"Error processing AddInData record: {e}")
                    continue
            
            print(f"Created mapping for {len(device_mapping)} devices (skipped {skipped_records} placeholder records)")
            
            # Process each device status record
            discrepancies_found = 0
            
            for device_status in device_status_list:
                try:
                    # Extract Geotab device info
                    device_id = device_status.get('device', {}).get('id')
                    geotab_lat = device_status.get('latitude')
                    geotab_lon = device_status.get('longitude')
                    
                    if not all([device_id, geotab_lat is not None, geotab_lon is not None]):
                        print(f"Skipping device with incomplete data: {device_id}")
                        continue
                    
                    geotab_coords = (geotab_lon, geotab_lat)
                    print(f"\nProcessing device {device_id} - Geotab coords: {geotab_coords}")
                    
                    # Check if we have Ruckit mapping for this device
                    if device_id not in device_mapping:
                        print(f"No Ruckit mapping found for device {device_id}")
                        continue
                    
                    ruckit_info = device_mapping[device_id]
                    
                    # Get latest location from Ruckit
                    ruckit_response = self.get_ruckit_location_updates(
                        ruckit_info['ri_token'], 
                        ruckit_info['ri_driver']
                    )
                    
                    if not ruckit_response or 'results' not in ruckit_response:
                        print(f"No Ruckit location data for device {device_id}")
                        continue
                    
                    results = ruckit_response['results']
                    if not results:
                        print(f"Empty results from Ruckit for device {device_id}")
                        continue
                    
                    # Get the most recent location update
                    latest_update = max(results, key=lambda x: x.get('date', ''))
                    location_obj = latest_update.get('location', {})
                    
                    ruckit_coords = self.extract_coordinates(location_obj)
                    if not ruckit_coords:
                        print(f"Could not extract coordinates from Ruckit data for device {device_id}")
                        continue
                    
                    print(f"Ruckit coords: {ruckit_coords}")
                    print(f"Latest update date: {latest_update.get('date')}")
                    
                    # Compare coordinates
                    if not self.coordinates_match(geotab_coords, ruckit_coords):
                        print(f"DISCREPANCY FOUND for device {device_id}!")
                        print(f"  Geotab: {geotab_coords}")
                        print(f"  Ruckit: {ruckit_coords}")
                        
                        # Call the POST function
                        self.post_location_update_to_ruckit(
                            ruckit_info['ri_token'],
                            ruckit_info['ri_device'],
                            ruckit_info['ri_driver'],
                            device_id,
                            device_status 
                        )
                        
                        discrepancies_found += 1
                    else:
                        print(f"Coordinates match for device {device_id}")
                
                except Exception as e:
                    print(f"Error processing device {device_id}: {e}")
                    continue
            
            print(f"\n=== Sync completed. Found {discrepancies_found} discrepancies ===")
            
        except Exception as e:
            print(f"Error in location sync process: {e}")
    
    def scheduler_loop(self):
        """Main scheduler loop that runs every 2 minutes"""
        print("Location sync scheduler started. Running every 2 minutes...")
        
        while self.running:
            try:
                if not self.authenticate_geotab():
                    print("Failed to authenticate with Geotab. Retrying in 2 minutes...")
                    time.sleep(120)  # 2 minutes
                    continue
                
                # Process location sync
                self.process_location_sync()
                
                # Wait for 2 minutes
                if self.running:
                    print(f"Waiting 2 minutes until next sync...")
                    time.sleep(120)  # 2 minutes
                    
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
                time.sleep(120)  # Wait 2 minutes before retrying
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            print("Scheduler is already running!")
            return
        
        # Initial authentication
        if not self.authenticate_geotab():
            print("Failed to authenticate with Geotab. Cannot start scheduler.")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        print("Scheduler started successfully!")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            print("Scheduler is not running!")
            return
        
        print("Stopping scheduler...")
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        print("Scheduler stopped.")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Configuration from environment variables
    GEOTAB_USERNAME = os.getenv("GEOTAB_USERNAME")
    GEOTAB_DATABASE = os.getenv("GEOTAB_DATABASE")
    GEOTAB_PASSWORD = os.getenv("GEOTAB_PASSWORD")
    
    if not all([GEOTAB_USERNAME, GEOTAB_DATABASE, GEOTAB_PASSWORD]):
        print("Error: Missing required environment variables. Please check your .env file.")
        exit(1)
    
    # Create and start the scheduler
    scheduler = LocationSyncScheduler(
        geotab_username=GEOTAB_USERNAME,
        geotab_database=GEOTAB_DATABASE,
        geotab_password=GEOTAB_PASSWORD
    )
    
    try:
        # Start the scheduler
        scheduler.start()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nReceived interrupt signal...")
        scheduler.stop()
        print("Program exited cleanly.")