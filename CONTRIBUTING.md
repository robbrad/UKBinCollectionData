**WIP**

# Contributor guidelines
The project uses [poetry](https://python-poetry.org/docs/) to manage dependencies and setup the build environment

# Getting Started
## Environment Setup
```
#install Python 3.8 or 3.9 (currently only these two are supported 3.10 in the future)
pip install poetry

#Clone the Repo
git clone https://github.com/robbrad/UKBinCollectionData
cd UKBinCollectionData

#Install Dependencies 
poetry install
poetry shell
```

# What you need for a council
## Approach
This repo uses a design pattern called the [Template Method](https://refactoring.guru/design-patterns/template-method) Basically allows for a structured class that can be extended. In our case the getting of the data from the council and the presentation of the JSON remains the same via the [abstract class](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/get_bin_data.py#L21) - however the scraping via [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) of each council is differnt and this allows us to have a class for each [council](https://github.com/robbrad/UKBinCollectionData/tree/master/uk_bin_collection/uk_bin_collection/councils) - you can see this in action [here](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/councils/CheshireEastCouncil.py#L5,L16)

To simplify things somewhat we have provided a "[CouncilClassTemplate](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/uk_bin_collection/councils/councilclasstemplate.py)" you can copy for your council to get things started

Its important to note the name of the council class file will be used on the CLI - eg if you take CheshireEastCouncil the result will be python collect_data.py **CheshireEastCouncil**

## Testing
### Behave (Integration Testing)
As with any "Scraping" project - it relies on the council not changing their website - if this happens beautiful soup can't read the site any longer and the data is not returned. To mitigate this and stay on top of "what works and what needs work" - We have created a set of Integration tests which run a [feature](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/tests/features/validate_council_outputs.feature) file. based on the [input.json](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/tests/input.json) this does an actaul live run against the council and validates the returned data is JSON and conforms to a [JSON Schema](https://github.com/robbrad/UKBinCollectionData/tree/master/uk_bin_collection/tests/council_schemas) for that council.

#### The input.json
The input.json should match the council class name eg CheshireEastCouncil and have a property per argument you want to supply eg url / uprn / postcode

**Note:** If you want the intergration test to work you must supply an actual working url / urpn / postcode (I usually choose a business address - the councils is a good one) so people dont get upset that their address was used for testing)

Example:
```
    "CheshireEastCouncil": {
        "url": "https://online.cheshireeast.gov.uk/MyCollectionDay/SearchByAjax/GetBartecJobList?uprn=100012791226&onelineaddress=3%20COBBLERS%20YARD,%20SK9%207DZ&_=1621149987573",
        "uprn": "100012791226"
    }
```

#### The schemas
Generate an output for a council and pass it though the [JSON schema converter](https://jsonformatter.org/json-to-jsonschema) save the file with the same name as the class eg CheshireEastCouncil.schema in the [schemas folder](https://github.com/robbrad/UKBinCollectionData/tree/master/uk_bin_collection/tests/council_schemas)

#### The feature file
The feature file will remain mostly static but if you want the feature to run for a specific council(again it must match the name of the council under test) then it needs adding as a line item in this file [table](https://github.com/robbrad/UKBinCollectionData/blob/master/uk_bin_collection/tests/features/validate_council_outputs.feature)

#### Running The behave suite of tests
```
cd UKBinCollectionData
poetry shell
behave -D runner.continue_after_failed_step=true uk_bin_collection/tests/features/
```

#### Github Actions Integration Tests
The [Github actions](https://github.com/robbrad/UKBinCollectionData/actions/workflows/behave.yml) is set to run on push and pull_requests

It uses a [Makefile](https://github.com/robbrad/UKBinCollectionData/blob/master/Makefile) to run the Behave tests to ensure the councils are all still working

#### Results

##### Allure Report
The Github Actions publishes the Allure Behave Test results to [Github Pages](https://robbrad.github.io/UKBinCollectionData/) you can check this to see if a council is still working as expected

##### CodeCov Report
The CodeCov.io report can be found [here](https://app.codecov.io/gh/robbrad/UKBinCollectionData) 

### Pytest (Unit Testing)
As well as integration testing the repo is setup to test some of the stactic methods as well to ensure basic core functionality

#### Running the Unitests
```
cd UKBinCollectionData
poetry shell
poetry run coverage run -m pytest
poetry run coverage xml
```

