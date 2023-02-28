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
- [Bromley Borough Council](#bromley-borough-council)
- [Cardiff Council](#cardiff-council)
- [Castlepoint District Council](#castlepoint-district-council)
- [Charnwood Borough Council](#charnwood-borough-council)
- [Chelmsford City Council](#chelmsford-city-council)
- [Cheshire East Council](#cheshire-east-council)
- [Chilterns](#chilterns)
- [Crawley Borough Council](#crawley-borough-council)
- [Croydon Council](#croydon-council)
- [Doncaster Council](#doncaster-council)
- [Durham Council](#durham-council)
- [Durham County Council](#durham-county-council)
- [East Cambridgeshire Council](#east-cambridgeshire-council)
- [East Devon District Council](#east-devon-district-council)
- [East Northampshire Council](#east-northampshire-council)
- [East Riding Council](#east-riding-council)
- [Erewash Borough Council](#erewash-borough-council)
- [Fenland District Council](#fenland-district-council)
- [Glasgow City Council](#glasgow-city-council)
- [High Peak Council](#high-peak-council)
- [Huntingdon District Council](#huntingdon-district-council)
- [Kingston Upon Thames Council](#kingston-upon-thames-council)
- [Leeds City Council](#leeds-city-council)
- [London Borough Hounslow](#london-borough-hounslow)
- [Maldon District Council](#maldon-district-council)
- [Malvern Hills District Council](#malvern-hills-district-council)
- [Manchester City Council](#manchester-city-council)
- [Mid Sussex District Council](#mid-sussex-district-council)
- [Newark and Sherwood District Council](#newark-and-sherwood-district-council)
- [Newcastle City Council](#newcastle-city-council)
- [North East Lincolnshire Council](#north-east-lincolnshire-council)
- [North Kesteven District Council](#north-kesteven-district-council)
- [North Lanarkshire Council](#north-lanarkshire-council)
- [North Lincolnshire Council](#north-lincolnshire-council)
- [North Somerset Council](#north-somerset-council)
- [North Tyneside Council](#north-tyneside-council)
- [Rochdale Council](#rochdale-council)
- [Sheffield City Council](#sheffield-city-council)
- [Somerset Council](#somerset-council)
- [South Ayrshire Council](#south-ayrshire-council)
- [South Lanarkshire Council](#south-lanarkshire-council)
- [South Norfolk Council](#south-norfolk-council)
- [South Oxfordshire Council](#south-oxfordshire-council)
- [South Tyneside Council](#south-tyneside-council)
- [St Helens Borough Council](#st-helens-borough-council)
- [Stockport Borough Council](#stockport-borough-council)
- [Tameside Metropolitan Borough Council](#tameside-metropolitan-borough-council)
- [Tonbridge and Malling Borough Council](#tonbridge-and-malling-borough-council)
- [Torbay Council](#torbay-council)
- [Torridge District Council](#torridge-district-council)
- [Vale of Glamorgan Council](#vale-of-glamorgan-council)
- [Wakefield City Council](#wakefield-city-council)
- [Warwick District Council](#warwick-district-council)
- [Waverley Borough Council](#waverley-borough-council)
- [Wealden District Council](#wealden-district-council)
- [Wigan Borough Council](#wigan-borough-council)
- [Windsor and Maidenhead Council](#windsor-and-maidenhead-council)
- [York Council](#york-council)

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

### Bromley Borough Council
```commandline
python collect_data.py BromleyBoroughCouncil https://recyclingservices.bromley.gov.uk/waste/XXXXXXX
```
Note: Follow the instructions [here](https://recyclingservices.bromley.gov.uk/waste) until the "Your bin days" page then copy the URL and replace the URL in the command.

---

### Cardiff Council
```commandline
python collect_data.py CardiffCouncil https://www.cardiff.gov.uk/ENG/resident/Rubbish-and-recycling/When-are-my-bins-collected/Pages/default.aspx -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Castlepoint District Council
```commandline
python collect_data.py CastlepointDistrictCouncil "https://apps.castlepoint.gov.uk/cpapps/index.cfm?fa=wastecalendar" -u XXXXXXXX -s true
```
Additional parameters:
- `-u` - UPRN

---

### Charnwood Borough Council
```commandline
python collect_data.py CharnwoodBoroughCouncil https://my.charnwood.gov.uk/
```

---

### Chelmsford City Council
```commandline
python collect_data.py CastlepointDistrictCouncil https://mychelmsford.secure.force.com/WasteServices/WM_WasteViewProperty?id=XXXXXXXX
```
Note: Replace XXXXXXXX with UPRN.

---

### Cheshire East Council
```commandline
python collect_data.py CheshireEastCouncil "https://online.cheshireeast.gov.uk/MyCollectionDay/SearchByAjax/GetBartecJobList?uprn=XXXXXXXX&onelineaddress=XXXXXXXX&_=1621149987573"
```
Note: 
Both the UPRN and a one-line address are passed in the URL, which needs to be wrapped in double quotes. The one-line address is made up of the house number, street name and postcode.
Use the form [here](https://online.cheshireeast.gov.uk/mycollectionday/) to find them, then take the first line and post code and replace all spaces with `%20`.

---

### Chilterns
```commandline
python collect_data.py Chilterns https://chiltern.gov.uk/collection-dates -p "XXX XXX" -n "XX XXXXX" -s true
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

Note: Pass the name of the street with the house number parameter, wrapped in double quotes

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

### Croydon Council
```commandline
python collect_data.py CroydonCouncil https://service.croydon.gov.uk/wasteservices/w/webpage/bin-day-enter-address -p "XXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

---

### Doncaster Council
```commandline
python collect_data.py DoncasterCouncil https://www.doncaster.gov.uk/Compass/Entity/Launch/D3/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Durham Council
```commandline
python collect_data.py DurhamCouncil https://www.durham.gov.uk/bincollections?uprn= -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Durham County Council
```commandline
python collect_data.py DurhamCountyCouncil http://mydurham.durham.gov.uk/article/12690?uprn=XXXXXXXXXXXXXXXXXXX -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### East Cambridgeshire Council
```commandline
python collect_data.py EastCambridgeshireCouncil https://eastcambs-self.achieveservice.com/appshost/firmstep/self/apps/custompage/bincollections?language=en&uprn= -u XXXXXXXX
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

### East Northampshire Council
```commandline
python collect_data.py EastNorthamptonshireCouncil https://kbccollectiveapi-coll-api.e4ff.pro-eu-west-1.openshiftapps.com/wc-info/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### East Riding Council
```commandline
python collect_data.py EastRidingCouncil https://waste-api.york.gov.uk/api/Collections/GetBinCollectionDataForUprn/ -p "XXX XXX"
```
Additional parameters:
- `-p` - postcode

---

### Erewash Borough Council
```commandline
python collect_data.py ErewashBoroughCouncil https://map.erewash.gov.uk/isharelive.web/myerewash.aspx -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Fenland District Council
```commandline
python collect_data.py FenlandDistrictCouncil https://www.fenland.gov.uk/article/13114/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Glasgow City Council
```commandline
python collect_data.py GlasgowCityCouncil https://www.glasgow.gov.uk/forms/refuseandrecyclingcalendar/PrintCalendar.aspx?UPRN=XXXXXXXX
```
Note: Replace XXXXXXXX with UPRN.

---

### High Peak Council
```commandline
python collect_data.py HighPeakCouncil https://www.highpeak.gov.uk/findyourbinday -p "XXX XXX" -n "XX XXXXX" -s true
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

Note: Pass the name of the street with the house number parameter, wrapped in double quotes

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

### London Borough Hounslow
```commandline
python collect_data.py LondonBoroughHounslow https://www.hounslow.gov.uk/homepage/86/recycling_and_waste_collection_day_finder -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Maldon District Council
```commandline
python collect_data.py MaldonDistrictCouncil https://maldon.suez.co.uk/maldon/ServiceSummary -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Malvern Hills District Council
```commandline
python collect_data.py MalvernHillsDC https://swict.malvernhills.gov.uk/mhdcroundlookup/HandleSearchScreen -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

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

### North East Lincolnshire Council
```commandline
python collect_data.py NorthEastLincs https://www.nelincs.gov.uk/refuse-collection-schedule/?uprn=XXXXXXXX&view=timeline
```
Note:
Replace XXXXXXXX with UPRN. Also ensure `&view=timeline` is kept on the end.

---

### North Kesteven District Council
```commandline
python collect_data.py NorthKestevenDistrictCouncil https://www.n-kesteven.org.uk/bins/display?uprn=XXXXXXXX
```
Note: Replace XXXXXXXX with UPRN.

---

### North Lanarkshire Council
```commandline
python collect_data.py NorthLanarkshireCouncil https://www.northlanarkshire.gov.uk/bin-collection-dates/XXXXXXXXXXX/XXXXXXXXXXX
```
Note: Follow the instructions [here](https://www.northlanarkshire.gov.uk/bin-collection-dates) until you get the "Next collections" page then copy the URL and replace the URL in the command.

---

### North Lincolnshire Council
```commandline
python collect_data.py NorthLincolnshireCouncil https://www.northlincs.gov.uk/bins-waste-and-recycling/bin-and-box-collection-dates/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### North Somerset Council
```commandline
python collect_data.py NorthSomersetCouncil https://forms.n-somerset.gov.uk/Waste/CollectionSchedule -p "XXXX XXX" -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### North Tyneside Council
```commandline
python collect_data.py NorthTynesideCouncil https://my.northtyneside.gov.uk/category/81/bin-collection-dates -p "XXXX XXX" -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### Rochdale Council
```commandline
python collect_data.py RochdaleCouncil https://webforms.rochdale.gov.uk/BinCalendar -p "XXXX XXX" -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### Sheffield City Council
```commandline
python collect_data.py SheffieldCityCouncil https://wasteservices.sheffield.gov.uk/property/XXXXXXXXXXX
```
Note: Follow the instructions [here](https://wasteservices.sheffield.gov.uk/) until you get the "Your bin collection dates and services" page then copy the URL and replace the URL in the command.

---

### Somerset Council
```commandline
python collect_data.py SomersetCouncil https://www.somerset.gov.uk/ -u XXXXXXXX -p "XXXX XXX"
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

### South Lanarkshire Council
```commandline
python collect_data.py SouthLanarkshireCouncil https://www.southlanarkshire.gov.uk/directory_record/XXXXX/XXXXX
```
Note: Follow the instructions [here](https://www.southlanarkshire.gov.uk/info/200156/bins_and_recycling/1670/bin_collections_and_calendar) until you get the page that shows the weekly collections for your street then copy the URL and replace the URL in the command.

---

### South Norfolk Council
```commandline
python collect_data.py SouthNorfolkCouncil https://www.southnorfolkandbroadland.gov.uk/rubbish-recycling/south-norfolk-bin-collection-day-finder -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

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

### Tameside Metropolitan Borough Council
```commandline
python collect_data.py TamesideMBCouncil http://lite.tameside.gov.uk/BinCollections/CollectionService.svc/GetBinCollection -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Tonbridge and Malling Borough Council
```commandline
python collect_data.py TonbridgeAndMallingBC https://www.tmbc.gov.uk/ -u XXXXXXXXXX -p "XXXX XXX"
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### Torbay Council
```commandline
python collect_data.py TorbayCouncil https://www.torbay.gov.uk/recycling/bin-collections/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

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

---

### York Council
```commandline
python collect_data.py YorkCouncil https://waste-api.york.gov.uk/api/Collections/GetBinCollectionDataForUprn/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN