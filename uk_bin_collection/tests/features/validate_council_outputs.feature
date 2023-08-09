Feature: Test each council output matches expected results in /outputs

    Scenario Outline: Validate Council Output
        Given the council: <council>
        When we scrape the data from <council>
        Then the result is valid json
        And the output should validate against the schema

        Examples: Testing : <council>
            | council |
            | AylesburyValueCouncil |
            | BasingstokeCouncil |
            | BCPCouncil |
            | BexleyCouncil |
            | BlackburnCouncil |
            | BoltonCouncil |
            | BristolCityCouncil |
            | BromleyBoroughCouncil |
            | BroxtoweBoroughCouncil |
            | CardiffCouncil |
            | CastlepointDistrictCouncil |
            | CharnwoodBoroughCouncil |
            | ChelmsfordCityCouncil |
            | CheshireEastCouncil |
            | Chilterns |
            | CrawleyBoroughCouncil |
            | CroydonCouncil |
            | DerbyshireDalesDistrictCouncil |
            | DoncasterCouncil |
            | DurhamCouncil |
            | EastCambridgeshireCouncil |
            | EastDevonDC |
            | EastleighBoroughCouncil |
            | EastNorthamptonshireCouncil |
            | EastRidingCouncil |
            | ErewashBoroughCouncil |
            | FenlandDistrictCouncil |
            | GlasgowCityCouncil |
            | HighPeakCouncil |
            | HuntingdonDistrictCouncil |
            | KingstonUponThamesCouncil |
            | LeedsCityCouncil |
            | LisburnCastlereaghCityCouncil |
            | LondonBoroughHounslow |
            | MaldonDistrictCouncil |
            | MalvernHillsDC |
            | ManchesterCityCouncil |
            | MertonCouncil |
            | MidSussexDistrictCouncil |
            | MiltonKeynesCityCouncil |
            | NewarkAndSherwoodDC |
            | NewcastleCityCouncil |
            | NorthEastLincs |
            | NorthKestevenDistrictCouncil |
            | NorthLanarkshireCouncil |
            | NorthLincolnshireCouncil |
            | NorthNorfolkDistrictCouncil |
            | NorthSomersetCouncil |
            | NorthTynesideCouncil |
            | NorthumberlandCouncil |
            | PrestonCityCouncil |
            | RochdaleCouncil |
            | RushcliffeBoroughCouncil |
            | RushmoorCouncil |
            | SalfordCityCouncil |
            | SheffieldCityCouncil |
            | SomersetCouncil |
            | SouthAyrshireCouncil |
            | SouthCambridgeshireCouncil |
            | SouthLanarkshireCouncil |
            | SouthNorfolkCouncil |
            | SouthOxfordshireCouncil |
            | SouthTynesideCouncil |
            | StHelensBC |
            | StockportBoroughCouncil |
            | SwaleBoroughCouncil |
            | TamesideMBCouncil |
            | TonbridgeAndMallingBC |
            | TorbayCouncil |
            | TorridgeDistrictCouncil |
            | ValeofGlamorganCouncil |
            | WakefieldCityCouncil |
            | WarwickDistrictCouncil |
            | WaverleyBoroughCouncil |
            | WealdenDistrictCouncil |
            | WelhatCouncil |
            | WiganBoroughCouncil |
            | WiltshireCouncil |
            | WindsorAndMaidenheadCouncil |
            | WokingBoroughCouncil |
            | YorkCouncil |
