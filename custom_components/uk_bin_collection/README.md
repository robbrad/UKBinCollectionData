# UK Bin Collection Integration for Home Assistant

The UK Bin Collection Integration for Home Assistant collects and presents information about forthcoming bin collections for your property. It achieves this by querying your council's website.

---

## Table of Contents

- [UK Bin Collection Integration for Home Assistant](#uk-bin-collection-integration-for-home-assistant)
  - [Table of Contents](#table-of-contents)
  - [Setup Process](#setup-process)
  - [Step 1: Name and Council](#step-1-name-and-council)
  - [Step 2: Council-Specific Details](#step-2-council-specific-details)
  - [Step 3: Selenium Configuration (if required)](#step-3-selenium-configuration-if-required)
  - [Step 4: Advanced Settings](#step-4-advanced-settings)
  - [Reconfiguration / Options Flow](#reconfiguration--options-flow)
  - [Validation Requirements](#validation-requirements)
  - [Icon Color Mapping JSON Example](#icon-color-mapping-json-example)
  - [Service: `uk_bin_collection.manual_refresh`](#service-uk_bin_collectionmanual_refresh)
    - [Service Data](#service-data)
    - [How the Service Works](#how-the-service-works)
  - [Example Automation to Refresh Bin Data (Manual Refresh Mode)](#example-automation-to-refresh-bin-data-manual-refresh-mode)

---

## Setup Process

The configuration flow is divided into four steps, with some steps being skipped based on your selected council's requirements:

1. Name and Council
2. Information specific to your council
3. Selenium configuration (if required)
4. Advanced settings

---

## Step 1: Name and Council

In the initial configuration step you must provide:

| Field Name              | Requirement | Type    | Description |
|-------------------------|-------------|---------|-------------|
| **name**                | Required    | String  | A unique identifier for your configuration entry. This is used to distinguish different configurations. |
| **council**             | Required    | Select  | A drop-down selection that displays available councils by their *wiki name*. Your selection will later be mapped to the corresponding council key. |

> **Note:** The list of available councils is dynamically loaded, and fields may be pre-populated based on your location. We have coverage for over 300 councils. If your council is missing or malfunctioning, please contact us.

---

## Step 2: Council-Specific Details

This step requests information specific to your selected council. The fields displayed depend on the council's requirements:

| Field Name         | Requirement                  | Type    | Description |
|--------------------|------------------------------|---------|-------------|
| **url**            | Required (if applicable)     | String  | The URL to access the bin collection data. Some councils require this field; however, if the council's configuration has `skip_get_url` enabled, this field may be pre-filled or skipped. |
| **uprn**           | Required (if applicable)     | String  | The Unique Property Reference Number, if the council supports it. |
| **postcode**       | Required (if applicable)     | String  | The postcode for the address in question. |
| **number**         | Required (if applicable)     | String  | The house number. (This corresponds to the `"house_number"` key in the council configuration.) |
| **usrn**           | Required (if applicable)     | String  | The Unique Street Reference Number, if required by the council. |

---

## Step 3: Selenium Configuration (if required)

This step is skipped if your council doesn't require Selenium.

Selenium is a system for scraping websites which we use for councils where a direct API is unavailable. It can be installed in a Docker container ([selenium/standalone-chrome](https://hub.docker.com/r/selenium/standalone-chrome)), either on the same device as Home Assistant or another computer.

| Field Name         | Requirement                  | Type    | Description |
|--------------------|------------------------------|---------|-------------|
| **web_driver**     | Optional (if applicable)     | String  | If the council requires Selenium for data fetching, you may provide the web driver command. |
| **headless**       | Optional (if applicable)     | Boolean | Indicates whether to run the browser in headless mode (default is `True`). Only shown if `web_driver` is applicable. |
| **local_browser**  | Optional (if applicable)     | Boolean | Choose whether to use a local browser instance (default is `False`). Only shown if `web_driver` is applicable. |

### Selenium & Chromium Checks

For councils that require Selenium:

- **Selenium Server Check:**  
  The integration checks some typical Selenium server URLs. If it doesn't find a working one, it will prompt to provide a working URL.

- **Chromium Installation Check:**  
  A check is performed to ensure that a local Chromium browser is installed.

---

## Step 4: Advanced Settings

The final step allows you to configure advanced options:

| Field Name              | Requirement | Type    | Description |
|-------------------------|-------------|---------|-------------|
| **manual_refresh_only** | Optional    | Boolean | If checked, only manual refreshes will be performed. Defaults to `False`. |
| **icon_color_mapping**  | Optional    | String  | A text field for entering a JSON-formatted mapping for icon colors. If provided, the JSON must be valid. |
| **timeout**             | Optional    | Integer | Sets the request timeout in seconds. Defaults to `60` seconds and must be at least `10`. |
| **update_interval**     | Optional    | Integer | The refresh frequency in hours. Defaults to `12` hours and must be at least `1`. |

---

## Reconfiguration

If you need to update your configuration later, you can do so via the "Configure" button in the UI. 

When reconfiguring a council, you'll find a new checkbox option:

| Field Name                                     | Requirement | Type    | Description |
|------------------------------------------------|-------------|---------|-------------|
| **Replace your council settings with test settings** | Optional    | Boolean | This is helpful when you want to establish whether the council is working with known working data. |

The remaining configuration fields will follow the same four-step process as the initial setup, allowing you to make adjustments as needed.

---

## Validation Requirements

- **Unique Name & Duplicate Check:**  
  The system checks to ensure that the provided `name` or combination of `council` and `url` is unique. If a duplicate entry exists, an error is shown.

- **JSON Format:**  
  Any input provided in the **icon_color_mapping** field must be valid JSON. If the JSON is invalid, you will be prompted to correct the input.

- **Numeric Ranges:**  
  - **Timeout:** Must be an integer and at least `10` seconds.
  - **Update Interval:** Must be an integer and at least `1` hour.

- **Council-Specific Fields:**  
  The required fields in the council-specific step depend on the selected council's configuration. Only the fields relevant to the chosen council will be presented.

---

## Icon Color Mapping JSON Example

Below is an example of a valid JSON configuration for the **icon_color_mapping** field. This mapping allows you to customize the icons and colors for different bin types in the sensor platform. The bin name **must match** the name of the bin returned from the council.

```json
{
  "general": {
    "icon": "mdi:trash-can",
    "color": "green"
  },
  "recycling": {
    "icon": "mdi:recycle",
    "color": "blue"
  },
  "food": {
    "icon": "mdi:food",
    "color": "red"
  },
  "garden": {
    "icon": "mdi:leaf",
    "color": "brown"
  }
}
```

## Service: `uk_bin_collection.manual_refresh`

This service triggers a manual refresh of the bin collection data for a specific configuration entry. It is particularly useful when your integration is set to **manual refresh only** (i.e., when the `manual_refresh_only` option is enabled in your configuration). When called, the service will instruct the data coordinator to fetch the latest bin collection data immediately.

### Service Data

| Field     | Type   | Description |
|-----------|--------|-------------|
| `entry_id` | String | **Required.** The unique identifier of the configuration entry. You can find this value in the integration details or in Home Assistant's configuration registry. |

### How the Service Works

1. **Input Verification:**  
   The service checks whether the `entry_id` is provided in the service call data.

2. **Configuration Entry Lookup:**  
   It verifies that a configuration entry exists for the provided `entry_id` in Home Assistant's data storage.

3. **Coordinator Check:**  
   It ensures that the corresponding data coordinator (which is responsible for fetching bin collection data) is available.

4. **Data Refresh:**  
   The service calls `async_request_refresh()` on the coordinator to fetch the latest data.

If any of these steps fail, error messages will be logged to help diagnose the issue.

---

## Example Automation to Refresh Bin Data (Manual Refresh Mode)

Below is an example automation that triggers a manual refresh of the bin collection data every day at 7:00 AM. This is useful if your integration is configured for manual refresh only. Be sure to replace `"YOUR_CONFIG_ENTRY_ID"` with the actual entry ID of your configuration.

```yaml
automation:
  - alias: "Daily Manual Refresh for UK Bin Collection"
    description: "Triggers a manual refresh of the bin collection data every day at 7 AM for integrations set to manual refresh only."
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: uk_bin_collection.manual_refresh
        data:
          entry_id: "YOUR_CONFIG_ENTRY_ID"
    mode: single
```