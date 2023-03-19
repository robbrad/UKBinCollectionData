# Contents
- [Contents](#contents)
- [Contributor guidelines](#contributor-guidelines)
  * [Getting Started](#getting-started)
    + [Environment Setup](#environment-setup)
  * [Project Aims](#project-aims)
    + [What can I contribute to?](#what-can-i-contribute-to-)
- [Adding a scraper](#adding-a-scraper)
  * [Approach](#approach)
  * [Developing](#developing)
    + [Kwargs](#kwargs)
    + [Common Functions](#common-functions)
  * [Additional files](#additional-files)
    + [Input JSON file](#input-json-file)
    + [Output JSON file](#output-json-file)
    + [Council schema](#council-schema)
    + [Feature file](#feature-file)
  * [Testing](#testing)
    + [Behave (Integration Testing)](#behave--integration-testing-)
      - [Running the Behave tests](#running-the-behave-tests)
      - [GitHub Actions Integration Tests](#github-actions-integration-tests)
      - [Test Results](#test-results)
        * [Allure Report](#allure-report)
        * [CodeCov Report](#codecov-report)
    + [Pytest (Unit Testing)](#pytest--unit-testing-)
      - [Running the Unittests](#running-the-unittests)
- [Contact info](#contact-info)


# Contributor guidelines
This document contains guidelines on contributing to the UKBCD project including how the project works, how to set up
the environment, how we use our issue tracker, and how you can develop more scrapers.

## Getting Started
You will need to install Python on the system you plan to run the script from. Python 3.8 and 3.9 are officially supported.
Python 3.10 and 3.11 should work, but your mileage _may_ vary.

The project uses [poetry](https://python-poetry.org/docs/) to manage dependencies and setup the build environment.

### Environment Setup
```
pip install poetry

# Clone the Repo
git clone https://github.com/robbrad/UKBinCollectionData
cd UKBinCollectionData

#Install Dependencies 
poetry install
poetry shell
```
## Project Aims
- To provide a real-world environment to learn Python and/or web scraping
- To provide UK bin data in a standardised format for use (albeit not exclusively) with [HomeAssistant](https://www.home-assistant.io/)

### What can I contribute to?
- The majority of project work comes from developing new scrapers for requested councils. These can be found on the [issue tracker](https://github.com/robbrad/UKBinCollectionData/labels/council%20request) with `council request` labels.
- Tasks that require [additional input](https://github.com/robbrad/UKBinCollectionData/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) have the `help wanted` label - these can be trickier requests or may have many smaller tasks.
- [Easier tasks](https://github.com/robbrad/UKBinCollectionData/labels/good%20first%20issue), that would be a good fit for people new to the project or the world of web scraping are labelled with the `good first issue` label



# Adding a scraper
## Approach
This repo uses a design pattern called the [Template Method](https://refactoring.guru/design-patterns/template-method) which basically allows for a structured class that can be extended. In our case, the getting of the data from the council and the presentation of the JSON remains the same via the [abstract class](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/get_bin_data.py#L21) - however the scraping of each council is different and this allows us to have a class for each [council](https://github.com/robbrad/UKBinCollectionData/tree/master/uk_bin_collection/uk_bin_collection/councils) - you can see this in action [here](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/councils/CheshireEastCouncil.py#L5,L16).

There are a few different options for scraping, and you are free to choose whichever best suits the council:
- Using [Beautiful Soup 4](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/councils/CheshireEastCouncil.py)
- Using the [requests](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/councils/ManchesterCityCouncil.py) module
- Reading data from [external files](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/councils/LeedsCityCouncil.py)
- Using [Selenium](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/councils/Chilterns.py) to automate browser behaviour

## Developing
To get started, first you will need to fork this repository and setup your own working environment before you can start developing.

Once your environment is ready, create a new branch from your master/main branch and then create a new .py file within the `uk_bin_collection\councils` directory. The new .py file will be used in the CLI to call the parser, so be sure to pick a sensible name - e.g. CheshireEastCouncil.py is called with:
```
python collect_data.py CheshireEastCouncil <web-url>
```

To simplify things somewhat, a [template](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/councils/councilclasstemplate.py) file has been created - open this file, copy the contents to your new .py file and start from there. You are pretty much free to approach the scraping however you would like, but please ensure that:
- Your scraper returns a dictionary made up of the key "bins" and a value that is a list of bin types and collection dates (see [outputs folder](https://github.com/robbrad/UKBinCollectionData/tree/master/uk_bin_collection/tests/outputs) for examples).
- Any dates or times are formatted to standard UK formats (see [below](#common-functions))

### Kwargs
UKBCD has two mandatory parameters when it runs - the name of the parser (sans .py) and the URL from which to scrape. However, developers can also get the following data using `kwargs`:

| Parameter    | Prompt               | Notes                                    | kwargs.get               |
|--------------|----------------------|------------------------------------------|--------------------------|
| UPRN         | `-u` or `--uprn`     |                                          | `kwargs.get('uprn')`     |
| House number | `-n` or `--number`   | Sometimes called PAON                    | `kwargs.get('paon')`     |
| Postcode     | `-p` or `--postcode` | Needs to be wrapped in quotes on the CLI | `kwargs.get('postcode')` |

These parameters are useful if you're using something like the requests module and need to take additional user information into the request, such as:
```commandline
python collect_data.py LeedsCityCouncil https://www.leeds.gov.uk/residents/bins-and-recycling/check-your-bin-day -p "LS1 2JG" -n 41
```
 In the scraper, the following code takes the inputted parameters and uses them in two different variables:
```python
user_postcode = kwargs.get("postcode")
user_paon = kwargs.get("paon")
```
Each parameter also has its own validation method that should be called after the `kwargs.get`:
- `check_uprn()`
- `check_paon()`
- `check_postcode()`

The first two are simple validators - if the parameter is used but no value is given, they will throw an exception. `check_postcode()` works differently - 
instead making a call to the [postcodes.io](https://postcodes.io/) API to check if it exists or not. An exception will only be thrown here if the response code is not `HTTP 200`.

### Common Functions
The project has a small but growing library of functions (and the occasional variable) that are useful when scraping websites or calendars - aptly named [common.py](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/common.py).
Useful functions include:
- functions to [add ordinals](https://github.com/robbrad/UKBinCollectionData/blob/e49da2f43143ac7c65fbeaf35b5e86b3ea19e31b/uk_bin_collection/uk_bin_collection/common.py#L72) to dates (04 becomes 4th) or [remove them](https://github.com/robbrad/UKBinCollectionData/blob/e49da2f43143ac7c65fbeaf35b5e86b3ea19e31b/uk_bin_collection/uk_bin_collection/common.py#L86) (4th becomes 04)
- a function to check [if a date is a holiday](https://github.com/robbrad/UKBinCollectionData/blob/e49da2f43143ac7c65fbeaf35b5e86b3ea19e31b/uk_bin_collection/uk_bin_collection/common.py#L117) in a given part of the UK
- a function that returns the [dates of a given weekday](https://github.com/robbrad/UKBinCollectionData/blob/e49da2f43143ac7c65fbeaf35b5e86b3ea19e31b/uk_bin_collection/uk_bin_collection/common.py#L136) in N amounts of weeks
- a function that returns a [list of dates every N days](https://github.com/robbrad/UKBinCollectionData/blob/e49da2f43143ac7c65fbeaf35b5e86b3ea19e31b/uk_bin_collection/uk_bin_collection/common.py#L148) from a given start date

`common.py` also contains a [standardised date format](https://github.com/robbrad/UKBinCollectionData/blob/e49da2f43143ac7c65fbeaf35b5e86b3ea19e31b/uk_bin_collection/uk_bin_collection/common.py#L11) variable called `date_format`, which is useful to call when formatting datetimes.

Please feel free to contribute to this library as you see fit - added functions should include the following:
- clear, lowercase and underscored name
- parameter types
- a return type (if there is one)
- a docustring describing what the function does, as well as parameter and return type descriptors.

## Additional files
In order for your scraper to work with the project's testing suite, some additional files need to be provided or
modified:
- [ ] [Input JSON file](#input-json-file)
- [ ] [Output JSON file](#output-json-file)
- [ ] [Council Schema](#council-schema)
- [ ] [Feature file](#feature-file)

**Note:** from here on, anything containing`<council_name>` should be replaced with the scraper's name.

### Input JSON file
| Type   | File location                                            |
|--------|----------------------------------------------------------|
| Modify | `UKBinCollectionData/uk_bin_collection/tests/input.json` |

Each council should have a node that matches the scraper's name. The node should include arguments in curly braces - the
URL is mandatory, but any additional parameters like UPRN or postcode should also be provided. Councils should be
listed in alphabetical order.

A "wiki_name" argument with the council's full name should also be provided.

A "wiki_note" argument should be used where non-standard instructions of just providing UPRN/Postcode/House Number
parameters are needed.

A "wiki_command_url_override" argument should be used where parts of the URL need to be replaced by the user to allow a
valid URL to be left for the integration tests.

A new [Wiki](https://github.com/robbrad/UKBinCollectionData/wiki/Councils) entry will be generated automatically from
this file's details.

**Note:** If you want the integration test to work you must supply real, working data (a business address is 
recommended - the council's address is usually a good one).

<details>
  <summary>Example</summary>

```json
    "CheshireEastCouncil": {
        "uprn": "100012791226",
        "url": "https://online.cheshireeast.gov.uk/MyCollectionDay/SearchByAjax/GetBartecJobList?uprn=100012791226&onelineaddress=3%20COBBLERS%20YARD,%20SK9%207DZ&_=1621149987573",
        "wiki_name": "Cheshire East Council",
        "wiki_command_url_override": "https://online.cheshireeast.gov.uk/MyCollectionDay/SearchByAjax/GetBartecJobList?uprn=XXXXXXXX&onelineaddress=XXXXXXXX&_=1621149987573",
        "wiki_note": "Both the UPRN and a one-line address are passed in the URL, which needs to be wrapped in double quotes. The one-line address is made up of the house number, street name and postcode.\nUse the form [here](https://online.cheshireeast.gov.uk/mycollectionday/) to find them, then take the first line and post code and replace all spaces with `%20`."
    },
```
</details>

### Output JSON file
| Type | File location                                                             |
|------|---------------------------------------------------------------------------|
| Add  | `UKBinCollectionData/uk_bin_collection/tests/outputs/<council_name>.json` |

A sample of what the scraper outputs should be provided in the [outputs](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/tests/outputs/)
folder. This can be taken from your development environment's console or a CLI. Please only include the "bins" data.

Adding the `-d` or `--dev_mode` parameter to your CLI command enables development mode which creates/updates the Output JSON file for the council automatically for you on each run

<details>
  <summary>Example</summary>

```json
{
    "bins": [
        {
            "bin_type": "Empty Standard Mixed Recycling",
            "collectionDate": "29/07/2022"
        },
        {
            "bin_type": "Empty Standard Garden Waste",
            "collectionDate": "29/07/2022"
        },
        {
            "bin_type": "Empty Standard General Waste",
            "collectionDate": "05/08/2022"
        }
    ]
}
```
</details>

### Council schema
| Type | File location                                                                       |
|------|-------------------------------------------------------------------------------------|
| Add  | `UKBinCollectionData/uk_bin_collection/tests/council_schemas/<council_name>.schema` |

Using the above [output](#output-json-file), you will need to generate a JSON schema that the integration test can run
against. Luckily, this is pretty easy and can be done using an [online tool](https://jsonformatter.org/json-to-jsonschema).

**Note:** due to seasonal collections (entirely dependent on council, of course), the schema may not include all bin types.
If this is the case, you may need to add them to the bin_type `enum` manually (usually around the end of the file).

<details>
  <summary>Example</summary>

```json
{
    "$schema": "http://json-schema.org/draft-06/schema#",
    "$ref": "#/definitions/Welcome10",
    "definitions": {
        "Welcome10": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
                "bins": {
                    "type": "array",
                    "items": {
                        "$ref": "#/definitions/Bin"
                    }
                }
            },
            "required": [
                "bins"
            ],
            "title": "Welcome10"
        },
        "Bin": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
                "bin_type": {
                    "$ref": "#/definitions/BinType"
                },
                "collectionDate": {
                    "type": "string"
                }
            },
            "required": [
                "bin_type",
                "collectionDate"
            ],
            "title": "Bin"
        },
        "BinType": {
            "type": "string",
            "enum": [
                "Empty Standard Mixed Recycling",
                "Empty Standard Garden Waste",
                "Empty Standard General Waste"
            ],
            "title": "BinType"
        }
    }
}
```
</details>

### Feature file
| Type   | File location                                                                           |
|--------|-----------------------------------------------------------------------------------------|
| Modify | `UKBinCollectionData/uk_bin_collection/tests/features/validate_council_outputs.feature` |

The council's name should be added to the feature file's example list. These names are alphabetically sorted, although
`council` should always remain on line 10. The name should be wrapped in pipes.


## Testing
### Behave (Integration Testing)
As with any web scraping project, there's a reliance on the council not changing their website - if this happens Beautiful Soup 
will fail to read the site correctly, and the expected data will not be returned. To mitigate this and stay on top 
of "what works and what needs work" - we have created a set of Integration tests which run a [feature](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/tests/features/validate_council_outputs.feature) 
file. 

Based on the [input.json](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/tests/input.json),
this does an actual live run against the council's site and validates if the returned data is JSON and conforms to a [JSON Schema](https://github.com/robbrad/UKBinCollectionData/tree/master/uk_bin_collection/tests/council_schemas) for that council.


#### Running the Behave tests
```commandline
cd UKBinCollectionData
poetry shell
poetry run pytest uk_bin_collection/tests/step_defs/ -n logical
```

#### GitHub Actions Integration Tests
The [GitHub actions](https://github.com/robbrad/UKBinCollectionData/actions/workflows/behave.yml) is set to run on push and pull_requests

It uses a [Makefile](https://github.com/robbrad/UKBinCollectionData/blob/master/Makefile) to run the [Behave](#behave--integration-testing-) tests to ensure the councils are all still working

#### Test Results

##### Allure Report
The Github Actions publishes the Allure Behave Test results to Github Pages: https://robbrad.github.io/UKBinCollectionData/<python_version>/ eg https://robbrad.github.io/UKBinCollectionData/3.9/ you can check this to see if a council is still working as expected

##### CodeCov Report
The CodeCov.io report can be found [here](https://app.codecov.io/gh/robbrad/UKBinCollectionData) 

### Pytest (Unit Testing)
As well as integration testing the repo is setup to test some of the static methods as well to ensure basic core functionality

#### Running the Unittests
```commandline
cd UKBinCollectionData
poetry shell
poetry run coverage run --omit "*/tests/*" -m pytest uk_bin_collection/tests --ignore=uk_bin_collection/tests/step_defs/
poetry run coverage xml
```

# Contact info
If you have questions or comments, you can reach the project contributors in the following ways:
- Council requests can be submitted [here](https://github.com/robbrad/UKBinCollectionData/issues/new?assignees=&labels=Class%3A+enhancement&template=COUNCIL_REQUEST.yaml)
- General questions or comments can be submitted [here](https://github.com/robbrad/UKBinCollectionData/discussions/categories/q-a)

