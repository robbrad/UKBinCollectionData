<!-- THIS FILE IS AUTO-GENERATED ANY CHANGES WILL BE OVERWRITTEN -->
<!-- Update `uk_bin_collection/tests/input.json` to make changes to this file -->

This Markdown document provides a list of commands and parameters for use with this script.

As a reminder, most scripts only need a module name and a URL to run, but others need more parameters depending on how the data is scraped.

For scripts that need postcodes, these should be provided in double quotes and with a space, e.g. `"AA1 2BB"` rather than `AA12BB`.

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
- [East Cambridgeshire Council](#east-cambridgeshire-council)
- [East Devon District Council](#east-devon-district-council)
- [Eastleigh Borough Council](#eastleigh-borough-council)
- [East Northamptonshire Council](#east-northamptonshire-council)
- [East Riding Council](#east-riding-council)
- [Erewash Borough Council](#erewash-borough-council)
- [Fenland District Council](#fenland-district-council)
- [Glasgow City Council](#glasgow-city-council)
- [High Peak Council](#high-peak-council)
- [Huntingdon District Council](#huntingdon-district-council)
- [Kingston Upon Thames Council](#kingston-upon-thames-council)
- [Leeds City Council](#leeds-city-council)
- [Lisburn and Castlereagh City Council](#lisburn-and-castlereagh-city-council)
- [London Borough Hounslow](#london-borough-hounslow)
- [Maldon District Council](#maldon-district-council)
- [Malvern Hills District Council](#malvern-hills-district-council)
- [Manchester City Council](#manchester-city-council)
- [Merton Council](#merton-council)
- [Mid Sussex District Council](#mid-sussex-district-council)
- [Milton Keynes City Council](#milton-keynes-city-council)
- [Newark and Sherwood District Council](#newark-and-sherwood-district-council)
- [Newcastle City Council](#newcastle-city-council)
- [North East Lincolnshire Council](#north-east-lincolnshire-council)
- [North Kesteven District Council](#north-kesteven-district-council)
- [North Lanarkshire Council](#north-lanarkshire-council)
- [North Lincolnshire Council](#north-lincolnshire-council)
- [North Somerset Council](#north-somerset-council)
- [North Tyneside Council](#north-tyneside-council)
- [Northumberland Council](#northumberland-council)
- [Rochdale Council](#rochdale-council)
- [Salford City Council](#salford-city-council)
- [Sheffield City Council](#sheffield-city-council)
- [Somerset Council](#somerset-council)
- [South Ayrshire Council](#south-ayrshire-council)
- [South Cambridgeshire Council](#south-cambridgeshire-council)
- [South Lanarkshire Council](#south-lanarkshire-council)
- [South Norfolk Council](#south-norfolk-council)
- [South Oxfordshire Council](#south-oxfordshire-council)
- [South Tyneside Council](#south-tyneside-council)
- [St Helens Borough Council](#st-helens-borough-council)
- [Stockport Borough Council](#stockport-borough-council)
- [Swale Borough Council](#swale-borough-council)
- [Tameside Metropolitan Borough Council](#tameside-metropolitan-borough-council)
- [Tonbridge and Malling Borough Council](#tonbridge-and-malling-borough-council)
- [Torbay Council](#torbay-council)
- [Torridge District Council](#torridge-district-council)
- [Vale of Glamorgan Council](#vale-of-glamorgan-council)
- [Wakefield City Council](#wakefield-city-council)
- [Warwick District Council](#warwick-district-council)
- [Waverley Borough Council](#waverley-borough-council)
- [Wealden District Council](#wealden-district-council)
- [Welhat Council](#welhat-council)
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
python collect_data.py BexleyCouncil https://www.bexley.gov.uk/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

Note: In order to use this parser, you will need to sign up to [Bexley's @Home app](https://www.bexley.gov.uk/services/rubbish-and-recycling/bexley-home-recycling-app/about-app) (available for [iOS](https://apps.apple.com/gb/app/home-collection-reminder/id1050703690) and [Android](https://play.google.com/store/apps/details?id=com.contender.athome.android)).
Complete the setup by entering your email and setting your address with postcode and address line.
Once you can see the calendar, you _should_ be good to run the parser.
Just pass the email you used in quotes in the UPRN parameter.


---

### Blackburn Council
```commandline
python collect_data.py BlackburnCouncil https://www.blackburn.gov.uk -s -u XXXXXXXX
```
Additional parameters:
- `-s` - skip get URL
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
python collect_data.py BristolCityCouncil https://bristolcouncil.powerappsportals.com/completedynamicformunauth/?servicetypeid=7dce896c-b3ba-ea11-a812-000d3a7f1cdc -u XXXXXXXX
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
python collect_data.py CastlepointDistrictCouncil https://apps.castlepoint.gov.uk/cpapps/index.cfm?fa=wastecalendar -s -u XXXXXXXX
```
Additional parameters:
- `-s` - skip get URL
- `-u` - UPRN

---

### Charnwood Borough Council
```commandline
python collect_data.py CharnwoodBoroughCouncil https://my.charnwood.gov.uk/location?put=cbcXXXXXXXX&rememberme=0&redirect=%2F
```

Note: Replace XXXXXXXX with UPRN keeping "cbc" before it.

---

### Chelmsford City Council
```commandline
python collect_data.py ChelmsfordCityCouncil https://www.chelmsford.gov.uk/myhome/XXXXXX
```

Note: Follow the instructions [here](https://www.chelmsford.gov.uk/myhome/) until you get the page listing your "Address", "Ward" etc then copy the URL and replace the URL in the command.

---

### Cheshire East Council
```commandline
python collect_data.py CheshireEastCouncil https://online.cheshireeast.gov.uk/MyCollectionDay/SearchByAjax/GetBartecJobList?uprn=XXXXXXXX&onelineaddress=XXXXXXXX&_=1621149987573 -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

Note: Both the UPRN and a one-line address are passed in the URL, which needs to be wrapped in double quotes. The one-line address is made up of the house number, street name and postcode.
Use the form [here](https://online.cheshireeast.gov.uk/mycollectionday/) to find them, then take the first line and post code and replace all spaces with `%20`.

---

### Chilterns
```commandline
python collect_data.py Chilterns https://chiltern.gov.uk/collection-dates -s -p "XXXX XXX" -n XX
```
Additional parameters:
- `-s` - skip get URL
- `-p` - postcode
- `-n` - house number

Note: Pass the name of the street with the house number parameter, wrapped in double quotes

---

### Crawley Borough Council
```commandline
python collect_data.py CrawleyBoroughCouncil https://my.crawley.gov.uk/
```

Note: Crawley needs both a UPRN and a USRN to work. You can either:
- Register with [OS Data Hub](https://osdatahub.os.uk/dashboard) and get an API key to find the USRN for you. You would have to place the API key in your own .env file within the project root,
  or change the variable on line 21, and remove the dependency and reference to `dotenv` on lines 5 and 20.
- Find the USRN on [FindMyAddress](https://www.findmyaddress.co.uk/search) or [FindMyStreet](https://www.findmystreet.co.uk/map) and hardcode the value in, again removing the dependency and reference to `dotenv` on lines 5 and 20.

---

### Croydon Council
```commandline
python collect_data.py CroydonCouncil https://service.croydon.gov.uk/wasteservices/w/webpage/bin-day-enter-address -p "XXXX XXX" -n XX
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

### East Cambridgeshire Council
```commandline
python collect_data.py EastCambridgeshireCouncil https://eastcambs-self.achieveservice.com/appshost/firmstep/self/apps/custompage/bincollections?language=en&uprn=XXXXXXXX
```

Note: Replace XXXXXXXX with UPRN.

---

### East Devon District Council
```commandline
python collect_data.py EastDevonDC https://eastdevon.gov.uk/recycling-and-waste/recycling-and-waste-information/when-is-my-bin-collected/future-collections-calendar/?UPRN=XXXXXXXX
```

Note: Replace XXXXXXXX with UPRN.

---

### Eastleigh Borough Council
```commandline
python collect_data.py EastleighBoroughCouncil https://www.eastleigh.gov.uk/waste-bins-and-recycling/collection-dates/your-waste-bin-and-recycling-collections?uprn= -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### East Northamptonshire Council
```commandline
python collect_data.py EastNorthamptonshireCouncil https://kbccollectiveapi-coll-api.e4ff.pro-eu-west-1.openshiftapps.com/wc-info/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### East Riding Council
```commandline
python collect_data.py EastRidingCouncil https://wasterecyclingapi.eastriding.gov.uk -p "XXXX XXX"
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
python collect_data.py HighPeakCouncil https://www.highpeak.gov.uk/findyourbinday -s -p "XXXX XXX" -n XX
```
Additional parameters:
- `-s` - skip get URL
- `-p` - postcode
- `-n` - house number

Note: Pass the name of the street with the house number parameter, wrapped in double quotes

---

### Huntingdon District Council
```commandline
python collect_data.py HuntingdonDistrictCouncil https://www.huntingdonshire.gov.uk/refuse-calendar/XXXXXXXX
```

Note: Replace XXXXXXXX with UPRN.

---

### Kingston Upon Thames Council
```commandline
python collect_data.py KingstonUponThamesCouncil https://waste-services.kingston.gov.uk/waste/XXXXXXX
```

Note: Follow the instructions [here](https://waste-services.kingston.gov.uk/waste) until the "Your bin days" page then copy the URL and replace the URL in the command.

---

### Leeds City Council
```commandline
python collect_data.py LeedsCityCouncil https://www.leeds.gov.uk/residents/bins-and-recycling/check-your-bin-day -p "XXXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

---

### Lisburn and Castlereagh City Council
```commandline
python collect_data.py LisburnCastlereaghCityCouncil https://lisburn.isl-fusion.com -s -p "XXXX XXX" -n XX
```
Additional parameters:
- `-s` - skip get URL
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

### Merton Council
```commandline
python collect_data.py MertonCouncil https://myneighbourhood.merton.gov.uk/Wasteservices/WasteServices.aspx?ID=XXXXXXXX
```

Note: Follow the instructions [here](https://myneighbourhood.merton.gov.uk/Wasteservices/WasteServicesSearch.aspx) until you get the "Your recycling and rubbish collection days" page then copy the URL and replace the URL in the command (the Address parameter is optional).

---

### Mid Sussex District Council
```commandline
python collect_data.py MidSussexDistrictCouncil https://www.midsussex.gov.uk/waste-recycling/bin-collection/ -p "XXXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

Note: Pass the name of the street with the house number parameter, wrapped in double quotes

---

### Milton Keynes City Council
```commandline
python collect_data.py MiltonKeynesCityCouncil https://www.milton-keynes.gov.uk/waste-and-recycling/collection-days -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

Note: Pass the name of the estate with the UPRN parameter, wrapped in double quotes

---

### Newark and Sherwood District Council
```commandline
python collect_data.py NewarkAndSherwoodDC http://app.newark-sherwooddc.gov.uk/bincollection/calendar?pid=XXXXXXXX
```

Note: Replace XXXXXXXX with UPRN.

---

### Newcastle City Council
```commandline
python collect_data.py NewcastleCityCouncil https://community.newcastle.gov.uk/my-neighbourhood/ajax/getBinsNew.php?uprn=XXXXXXXX
```

Note: Replace XXXXXXXX with UPRN.

---

### North East Lincolnshire Council
```commandline
python collect_data.py NorthEastLincs https://www.nelincs.gov.uk/refuse-collection-schedule/?view=timeline&uprn=XXXXXXXX -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

Note: Replace XXXXXXXX with UPRN.

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
python collect_data.py NorthSomersetCouncil https://forms.n-somerset.gov.uk/Waste/CollectionSchedule -u XXXXXXXX -p "XXXX XXX"
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### North Tyneside Council
```commandline
python collect_data.py NorthTynesideCouncil https://my.northtyneside.gov.uk/category/81/bin-collection-dates -u XXXXXXXX -p "XXXX XXX"
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### Northumberland Council
```commandline
python collect_data.py NorthumberlandCouncil https://www.northumberland.gov.uk/Waste/Bins/Bin-Calendars.aspx -p "XXXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

---

### Rochdale Council
```commandline
python collect_data.py RochdaleCouncil https://webforms.rochdale.gov.uk/BinCalendar -u XXXXXXXX -p "XXXX XXX"
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### Salford City Council
```commandline
python collect_data.py SalfordCityCouncil https://www.salford.gov.uk/bins-and-recycling/bin-collection-days/your-bin-collections -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

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

### South Cambridgeshire Council
```commandline
python collect_data.py SouthCambridgeshireCouncil https://www.scambs.gov.uk/recycling-and-bins/find-your-household-bin-collection-day/ -p "XXXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

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
python collect_data.py StHelensBC https://secure.sthelens.net/website/CollectionDates.nsf/servlet.xsp/NextCollections?source=1&refid=XXXXXXXX
```

Note: Replace XXXXXXXX with UPRN.

---

### Stockport Borough Council
```commandline
python collect_data.py StockportBoroughCouncil https://myaccount.stockport.gov.uk/bin-collections/show/XXXXXXXX
```

Note: Replace XXXXXXXX with UPRN.

---

### Swale Borough Council
```commandline
python collect_data.py SwaleBoroughCouncil https://swale.gov.uk/bins-littering-and-the-environment/bins/collection-days -u XXXXXXXX -p "XXXX XXX"
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

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
python collect_data.py TonbridgeAndMallingBC https://www.tmbc.gov.uk/ -u XXXXXXXX -p "XXXX XXX"
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
python collect_data.py TorridgeDistrictCouncil https://collections-torridge.azurewebsites.net/WebService2.asmx -s -u XXXXXXXX
```
Additional parameters:
- `-s` - skip get URL
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
- `-u` - UPRN

Note: Replace XXXXXXXX with UPRN and also pass in -u parameter

---

### Warwick District Council
```commandline
python collect_data.py WarwickDistrictCouncil https://estates7.warwickdc.gov.uk/PropertyPortal/Property/Recycling/XXXXXXXX
```

Note: Replace XXXXXXXX with UPRN.

---

### Waverley Borough Council
```commandline
python collect_data.py WaverleyBoroughCouncil https://wav-wrp.whitespacews.com/ -p "XXXX XXX" -n XX
```
Additional parameters:
- `-p` - postcode
- `-n` - house number

Note: Follow the instructions [here](https://wav-wrp.whitespacews.com/#!) until you get the page that shows your next scheduled collections.
Then take the number from pIndex=NUMBER in the URL and pass it as the -n parameter along with your postcode in -p.

---

### Wealden District Council
```commandline
python collect_data.py WealdenDistrictCouncil https://www.wealden.gov.uk/recycling-and-waste/bin-search/ -u XXXXXXXX
```
Additional parameters:
- `-u` - UPRN

---

### Welhat Council
```commandline
python collect_data.py WelhatCouncil https://www.welhat.gov.uk/xfp/form/214 -u XXXXXXXX -p "XXXX XXX"
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### Wigan Borough Council
```commandline
python collect_data.py WiganBoroughCouncil https://apps.wigan.gov.uk/MyNeighbourhood/ -u XXXXXXXX -p "XXXX XXX"
```
Additional parameters:
- `-u` - UPRN
- `-p` - postcode

---

### Windsor and Maidenhead Council
```commandline
python collect_data.py WindsorAndMaidenheadCouncil https://my.rbwm.gov.uk/special/find-your-collection-dates -p "XXXX XXX" -n XX
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
