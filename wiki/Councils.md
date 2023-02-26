This markdown document provides a list of commands and parameters for use with this script.

As a reminder, most scripts only need a module name and a URL to run, but others need more parameters depending on how the data is scraped.

For scripts that need postcodes, these should be provided in double quotes and with a space, e.g.
`"AA1 2BB"` rather than `AA12BB`.

This document is still a work in progress, don't worry if your council isn't listed - it will be soon!

## Contents
- [BCP Council](#bcp-council)
- [Bexley Council](#bexley-council)
- [Blackburn Council](#blackburn-council)
- [Bolton Council](#bolton-council)
- [Bristol City Council](#bristol-city-council)
- [Cardiff Council](#cardiff-council)
- [Cheshire East Council](#cheshire-east-council)
- [Crawley Borough Council](#crawley-borough-council)
- [Doncaster Council](#doncaster-council)
- [East Devon District Council](#east-devon-district-council)
- [Fenland District Council](#fenland-district-council)
- [Huntingdon District Council](#huntingdon-district-council)
- [Kingston Upon Thames Council](#kingston-upon-thames-council)
- [Leeds City Council](#leeds-city-council)
- [Manchester City Council](#manchester-city-council)
- [Mid Sussex District Coucnil](#mid-sussex-district-council)
- [North East Lincolnshire Council](#north-east-lincolnshire-council)
- [Newark and Sherwood District Council](#newark-and-sherwood-district-council)
- [Newcastle City Council](#newcastle-city-council)
- [North Tyneside Council](#north-tyneside-council)
- [South Ayrshire Council](#south-ayrshire-council)
- [South Oxfordshire Council](#south-oxfordshire-council)
- [South Tyneside Council](#south-tyneside-council)
- [St Helens Borough Council](#st-helens-borough-council)
- [Stockport Borough Council](#stockport-borough-council)
- [Tonbridge and Malling Borough Council](#tonbridge-and-malling-borough-council)
- [Torridge District Council](#torridge-district-council)
- [Vale of Glamorgan Council](#vale-of-glamorgan-council)
- [Wakefield City Council](#wakefield-city-council)
- [Warwick District Council](#warwick-district-council)
- [Waverley Borough Council](#waverley-borough-council)
- [Wealden District Council](#wealden-district-council)
- [Wigan Borough Council](#wigan-borough-council)
- [Windsor and Maidenhead Council](#windsor-and-maidenhead-council)

---

### BCP Council
```commandline
python collect_data.py BCPCouncil https://online.bcpcouncil.gov.uk/bindaylookup/ -u XXXXXXXX
```

Additional parameters:
- `-u` - UPRN

---

### Bexley Council
```commandline
python collect_data.py BexleyCouncil https://www.bexley.gov.uk/ -u "XXXXXXXX@XXXX.XX.XX"
```
In order to use this parser, you will need to sign up to [Bexley's @Home app](https://www.bexley.gov.uk/services/rubbish-and-recycling/bexley-home-recycling-app/about-app) (available for [iOS](https://apps.apple.com/gb/app/home-collection-reminder/id1050703690) and [Android](https://play.google.com/store/apps/details?id=com.contender.athome.android)). Complete the setup by entering your email and setting your address with postcode and address line. Once you can see the calendar, you _should_ be good to run the parser. Just include the `-u` argument and include the email you used in quotes.


Additional parameters:
- `-u` - Email (let's pretend its a UPRN)

---

### Blackburn Council
```commandline
python collect_data.py BlackburnCouncil http://google.com -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Bolton Council
```commandline
python collect_data.py BoltonCouncil https://maps.bolton.gov.uk/residents/getdata.aspx?requesttype=LocalInfo&ms=Bolton/MyHouse&group=My%20house%20data%7Cbin_collections_combined&format=json&uid=XXXXXXXX
```
Note: Replace XXXXXXXX with UPRN.

---
### Bristol City Council
```commandline
python collect_data.py BristolCityCouncil https://bristolcouncil.powerappsportals.com/completedynamicformunauth/?servicetypeid=7dce896c-b3ba-ea11-a812-000d3a7f1cdc -u XXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Cardiff Council
```commandline
python collect_data.py CardiffCouncil https://www.cardiff.gov.uk/ENG/resident/Rubbish-and-recycling/When-are-my-bins-collected/Pages/default.aspx -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---
### Cheshire East Council
```commandline
python collect_data.py CheshireEastCouncil "https://online.cheshireeast.gov.uk/MyCollectionDay/SearchByAjax/GetBartecJobList?uprn=XXXXXXXX&onelineaddress=XXXXXXXX&_=1621149987573"
```
Note: 
Both the UPRN and a one-line address are passed in the URL, which needs to be wrapped in double quotes. The one-line address is made up of the house number, street name and postcode.
Use the form [here](https://online.cheshireeast.gov.uk/mycollectionday/) to find them, then take the first line and post code and replace all spaces with `%20`.

---
### Crawley Borough Council
```commandline
python collect_data.py CrawleyBoroughCouncil https://my.crawley.gov.uk/ -u XXXXXXXX
```
Note: Crawley needs both a UPRN and a USRN to work. You can either:
 - Register with [OS Data Hub](https://osdatahub.os.uk/dashboard) and get an API key to find the USRN for you. You would have to place the API key in your own .env file within the project root,
or change the variable on line 21, and remove the dependency and reference to `dotenv` on lines 5 and 20.
 - Find the USRN on [FindMyAddress](https://www.findmyaddress.co.uk/search) or [FindMyStreet](https://www.findmystreet.co.uk/map) and hardcode the value in, again removing the dependency and reference to `dotenv` on lines 5 and 20.

Additional parameters:
- `-u` - UPRN

---

### Doncaster Council
```commandline
python collect_data.py DoncasterCouncil https://www.doncaster.gov.uk/Compass/Entity/Launch/D3/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN


---
### East Devon District Council
```commandline
python collect_data.py EastDevonDC https://eastdevon.gov.uk/recycling-and-waste/recycling-and-waste-information/when-is-my-bin-collected/future-collections-calendar/?UPRN=XXXXXXXX
```
Note: make sure the URL includes `/future-collections-calendar/` for this script to work properly

---
### Fenland District Council
```commandline
python collect_data.py FenlandDistrictCouncil https://www.fenland.gov.uk/article/13114/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---
### Huntingdon District Council
```commandline
python collect_data.py HuntingdonDistrictCouncil https://www.huntingdonshire.gov.uk/refuse-calendar/XXXXXXXX
```
Note: Replace XXXXXXXX with the UPRN of the property

---
### Kingston Upon Thames Council
```commandline
python collect_data.py KingstonUponThamesCouncil https://waste-services.kingston.gov.uk/waste/XXXXXXX
```
Note: Follow the instructions [here](https://waste-services.kingston.gov.uk/waste) until the "Your bin days" page then copy the URL and replace the URL in the command.

---
### Leeds City Council
```commandline
python collect_data.py LeedsCityCouncil https://www.leeds.gov.uk/residents/bins-and-recycling/check-your-bin-day -p "XXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - house number
---

### Manchester City Council
```commandline
python collect_data.py ManchesterCityCouncil https://www.manchester.gov.uk/bincollections -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---
### Mid Sussex District Council
```commandline
python collect_data.py MidSussexDistrictCouncil https://www.midsussex.gov.uk/waste-recycling/bin-collection/ -p "XXXX XXX" -n "XX XXXXXXXX"
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

Note: pass the name of the street with the house number parameter, wrapped in double quotes (*I couldn't think of a better way of adding support for this easily, but its needed for form data*)

---

### North East Lincolnshire Council
```commandline
python collect_data.py NELincs https://www.nelincs.gov.uk/refuse-collection-schedule/?uprn=XXXXXXXX&view=timeline
```
Note:
Replace XXXXXXXX with UPRN. Also ensure `&view=timeline` is kept on the end.

---
### Newark and Sherwood District Council
```commandline
python collect_data.py NewarkAndSherwoodDC http://app.newark-sherwooddc.gov.uk/bincollection/calendar?pid=XXXXXXXX
```
Note: Replace XXXXXXXX with UPRN.

---

### Newcastle City Council
```commandline
python collect_data.py NewcastleCityCouncil https://community.newcastle.gov.uk/my-neighbourhood/ajax/getBinsNew.php?uprn=XXXXXXXXXXXX
```
Note: Replace XXXXXXXX with UPRN.

---

### North Tyneside Council
```commandline
python collect_data.py NorthTynesideCouncil https://my.northtyneside.gov.uk/category/81/bin-collection-dates -p "XXXX XXX" -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### South Ayrshire Council
```commandline
python collect_data.py SouthAyrshireCouncil https://www.south-ayrshire.gov.uk/ -u XXXXXXXX -p "XXXX XXX"
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---
### South Oxfordshire Council
```commandline
python collect_data.py SouthOxfordshireCouncil https://www.southoxon.gov.uk/south-oxfordshire-district-council/recycling-rubbish-and-waste/when-is-your-collection-day/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---
### South Tyneside Council
```commandline
python collect_data.py SouthTynesideCouncil https://www.southtyneside.gov.uk/article/33352/Bin-collection-dates -p "XXXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

---
### St Helens Borough Council
```commandline
python collect_data.py StHelensBC https://secure.sthelens.net/website/CollectionDates.nsf/servlet.xsp/NextCollections?refid=XXXXXXXX&source=1
```
Note: Replace XXXXXXXX with UPRN.

---
### Stockport Borough Council
```commandline
python collect_data.py StockportBoroughCouncil https://myaccount.stockport.gov.uk/bin-collections/show/XXXXXXXX
```
Note: Replace XXXXXXXX with UPRN.

---

### Tonbridge and Malling Borough Council
```commandline
python collect_data.py TonbridgeAndMallingBC https://www.tmbc.gov.uk/ -u XXXXXXXXXX -p "XXXX XXX"
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### Torridge District Council
```commandline
python collect_data.py TorridgeDistrictCouncil https://www.torridge.gov.uk/collectiondates -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN
---

### Vale of Glamorgan Council
```commandline
python collect_data.py ValeofGlamorganCouncil https://www.valeofglamorgan.gov.uk/en/living/Recycling-and-Waste/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---


### Wakefield City Council 
```commandline
python collect_data.py WakefieldCityCouncil https://www.wakefield.gov.uk/site/Where-I-Live-Results?uprn=XXXXXXXX -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN (needed in both the URL and `-u` argument)

---
### Warwick District Council
```commandline
python collect_data.py WarwickDistrictCouncil https://estates7.warwickdc.gov.uk/PropertyPortal/Property/Recycling/XXXXXXXX
```
Note: Replace XXXXXXXX with UPRN.

---

### Waverley Borough Council
```commandline
python collect_data.py WaverleyBoroughCouncil https://wav-wrp.whitespacews.com/ -p "XXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - this is actually not the house number - it is a unique identifier specific to the council for identifying the property (like a house number but I have no idea why its different). To find it, use the online form to enter your postcode/get your house number. At the end of the URL, there will be something like "&pIndex=1" - that's the number you need (and only the number)

---

### Wealden District Council
```commandline
python collect_data.py WealdenDistrictCouncil https://www.wealden.gov.uk/recycling-and-waste/bin-search/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN
---

### Wigan Borough Council
```commandline
python collect_data.py WiganBoroughCouncil https://apps.wigan.gov.uk/MyNeighbourhood/ -u XXXXXXXXXXXX -p XXXXXX 
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### Windsor and Maidenhead Council
```commandline
python collect_data.py WindsorAndMaidenheadCouncil https://my.rbwm.gov.uk/special/your-collection-dates -p "XXXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - house number
