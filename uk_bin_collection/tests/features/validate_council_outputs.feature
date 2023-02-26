Feature: Test each council output matches expected results in /outputs

    Scenario Outline: Validate Council Output
        Given the council: "<council>"
        When we scrape the data from "<council>"
        Then the result is valid json
        And the output should validate against the schema

        Examples: Testing : <council>
            | council |
            #| BCPCouncil |
            #| BexleyCouncil |
            #| BlackburnCouncil |
            #| BoltonCouncil |
            #| BristolCityCouncil |
            #| BromleyBoroughCouncil |
            #| CardiffCouncil |
            #| CastlepointDistrictCouncil |
            #| CharnwoodBoroughCouncil |
            #| ChelmsfordCityCouncil |
            | CheshireEastCouncil |
            #| Chilterns |
            #| CrawleyBoroughCouncil |
            #| CroydonCouncil |
            #| DoncasterCouncil |
            #| DurhamCouncil |
            #| DurhamCountyCouncil |
            #| EastCambridgeshireCouncil |
            #| EastDevonDC |
            #| EastNorthamptonshireCouncil |
            #| EastRidingCouncil |
            #| ErewashBoroughCouncil |
            #| FenlandDistrictCouncil |
            #| GlasgowCityCouncil |
            #| HighPeakCouncil |
            #| HuntingdonDistrictCouncil |
            #| KingstonUponThamesCouncil |
            #| LeedsCityCouncil |
            #| LondonBoroughHounslow |
            #| MaldonDistrictCouncil |
            #| ManchesterCityCouncil |
            #| MidSussexDistrictCouncil |
            #| NewarkAndSherwoodDC |
            #| NewcastleCityCouncil |
            #| NorthEastLincs |
            #| NorthKestevenDistrictCouncil |
            #| NorthLanarkshireCouncil |
            #| NorthLincolnshireCouncil |
            #| NorthSomersetCouncil |
            #| NorthTynesideCouncil |
            #| RochdaleCouncil |
            #| SheffieldCityCouncil |
            #| SomersetCouncil |
            #| SouthAyrshireCouncil |
            #| SouthLanarkshireCouncil |
            #| SouthNorfolkCouncil |
            #| SouthOxfordshireCouncil |
            #| SouthTynesideCouncil |
            #| StHelensBC |
            #| StockportBoroughCouncil |
            #| TamesideMBCouncil |
            #| TonbridgeAndMallingBC |
            #| TorbayCouncil |
            #| TorridgeDistrictCouncil |
            #| ValeofGlamorganCouncil |
            #| WakefieldCityCouncil |
            #| WarwickDistrictCouncil |
            #| WaverleyBoroughCouncil |
            #| WealdenDistrictCouncil |
            #| WiganBoroughCouncil |
            #| WindsorAndMaidenheadCouncil |
            #| YorkCouncil |
