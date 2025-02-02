# UK Bin Collection Integration Configuration

This integration allows you to configure the collection details for your local UK council. The configuration flow is divided into several steps, and some fields are dynamically shown based on your selected council’s requirements.

---

## Table of Contents

- [UK Bin Collection Integration Configuration](#uk-bin-collection-integration-configuration)
  - [Table of Contents](#table-of-contents)
  - [Step 1: Basic Setup](#step-1-basic-setup)
  - [Step 2: Council-Specific Details](#step-2-council-specific-details)
    - [Selenium \& Chromium Checks](#selenium--chromium-checks)
  - [Reconfiguration / Options Flow](#reconfiguration--options-flow)
  - [Validation Requirements](#validation-requirements)
  - [Icon Color Mapping JSON Example](#icon-color-mapping-json-example)

---

## Step 1: Basic Setup

In the initial configuration step you must provide the following:

| Field Name              | Requirement | Type    | Description |
|-------------------------|-------------|---------|-------------|
| **name**                | Required    | String  | A unique identifier for your configuration entry. This is used to distinguish different configurations. |
| **council**             | Required    | Select  | A drop-down selection that displays available councils by their *wiki name*. Your selection will later be mapped to the corresponding council key. |
| **manual_refresh_only** | Optional    | Boolean | If checked, only manual refreshes will be performed. Defaults to `False`. |
| **icon_color_mapping**  | Optional    | String  | A text field for entering a JSON-formatted mapping for icon colors. If provided, the JSON must be valid. |

> **Note:** The list of available councils is dynamically loaded from an external data source.

---

## Step 2: Council-Specific Details

After you provide the basic details, the next step requests council-specific information. The fields displayed depend on the selected council’s requirements. Below is a summary of possible fields:

| Field Name         | Requirement                  | Type    | Description |
|--------------------|------------------------------|---------|-------------|
| **url**            | Required (if applicable)     | String  | The URL to access the bin collection data. Some councils require this field; however, if the council’s configuration has `skip_get_url` enabled, this field may be pre-filled or skipped. |
| **uprn**           | Required (if applicable)     | String  | The Unique Property Reference Number, if the council supports it. |
| **postcode**       | Required (if applicable)     | String  | The postcode for the address in question. |
| **number**         | Required (if applicable)     | String  | The house number. (This corresponds to the `"house_number"` key in the council configuration.) |
| **usrn**           | Required (if applicable)     | String  | The Unique Street Reference Number, if required by the council. |
| **web_driver**     | Optional (if applicable)     | String  | If the council requires Selenium for data fetching, you may provide the web driver command. |
| **headless**       | Optional (if applicable)     | Boolean | Indicates whether to run the browser in headless mode (default is `True`). Only shown if `web_driver` is applicable. |
| **local_browser**  | Optional (if applicable)     | Boolean | Choose whether to use a local browser instance (default is `False`). Only shown if `web_driver` is applicable. |
| **timeout**        | Optional                     | Integer | Sets the request timeout in seconds. Defaults to `60` seconds and must be at least `10`. |
| **update_interval**| Optional                     | Integer | The refresh frequency in hours. Defaults to `12` hours and must be at least `1`. |

### Selenium & Chromium Checks

For councils that require Selenium (i.e. if the council configuration contains a `"web_driver"` key):

- **Selenium Server Check:**  
  The integration checks several remote Selenium server URLs (and an optional custom URL, if provided) to determine if they are accessible. The results are displayed as part of the informational message.

- **Chromium Installation Check:**  
  A check is performed to ensure that a local Chromium browser is installed. The result is shown to help troubleshoot if Selenium is required.

The combined status of these checks is presented as an HTML-formatted message in the council-specific form.

---

## Reconfiguration / Options Flow

If you need to update your configuration later, you can do so via the options (or reconfiguration) flow. The following fields are available for editing:

| Field Name              | Requirement | Type    | Description |
|-------------------------|-------------|---------|-------------|
| **name**                | Required    | String  | The identifier for the configuration entry. |
| **council**             | Required    | Select  | A drop-down list to select your council (displayed by its *wiki name*). |
| **manual_refresh_only** | Optional    | Boolean | If enabled, the system will perform only manual refreshes. |
| **update_interval**     | Required    | Integer | The refresh frequency in hours (must be at least 1). If manual refresh is enabled, this will be set to `None`. |
| **icon_color_mapping**  | Optional    | String  | A JSON-formatted string for mapping icon colors. Must be valid JSON if provided. |

> **Additional Fields:**  
Depending on your initial configuration and the council selected, you may also be able to update fields such as **url**, **uprn**, **postcode**, **number**, **web_driver**, **headless**, **local_browser**, and **timeout**.

Once you submit the updated options, the integration will reload the configuration with the new settings.

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
  The required fields in the council-specific step (such as `url`, `uprn`, `postcode`, etc.) depend on the selected council's configuration. Only the fields relevant to the chosen council will be presented.

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
