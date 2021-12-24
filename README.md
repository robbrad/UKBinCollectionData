# UKBinCollectionData
UK Council Bin Collection Data Parser - Outputting Bin Data as a JSON

Born from https://community.home-assistant.io/t/bin-waste-collection/

Reference : https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/791684/List_of_councils_in_England_2019.pdf

This is a list of Python3 Scripts which use Beautiful Soup 4 to pull Bin Collection data into a JSON where a council does not provide a restful API - Yes Yes Yes any script could break when a council changes their site - but until they provide a service for programmatic consumption then stript on-ward. 

Please use responsibly - I take no responsibility for the use of these scripts, I created this to get better at Python and Beautiful Soup.

Please help raise an issue to creation for your council or contribute for your council via a pull request!

The dream would be to make each of these into one common lib


python collect_data.py <council_class_name> "<collection_url>"