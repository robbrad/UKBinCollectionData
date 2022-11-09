Feature: Test each council output matches expected results in /outputs

    Scenario Outline: Validate Council Output
        Given the council: "<council>"
        When we scrape the data from "<council>"
        Then the result is valid json
        And the output should validate against the schema

        Examples: Testing : <council>
            | council      |
            | BexleyCouncil |
            | BlackburnCouncil |
            | BoltonCouncil |
            | BristolCityCouncil |
            | CardiffCouncil |
            | CastlepointDistrictCouncil |
            | CheshireEastCouncil |
            | CrawleyBoroughCouncil |
            | DoncasterCouncil |
            | EastDevonDC |
            | FenlandDistrictCouncil |
            | HuntingdonDistrictCouncil |
            | LeedsCityCouncil |
            | ManchesterCityCouncil |
            | MidSussexDistrictCouncil |
            | NELincs |
            | NewarkAndSherwoodDC |
            | NewcastleCityCouncil |
            | SouthAyrshireCouncil |
            | SouthTynesideCouncil |
            | StHelensBC |
            | StockportBoroughCouncil |
            | TorridgeDistrictCouncil |
            | WakefieldCityCouncil |
            | WarwickDistrictCouncil |
            | WaverleyBoroughCouncil |
            | WealdenDistrictCouncil |
            | WiganBoroughCouncil |
            | WindsorAndMaidenheadCouncil |
            | YorkCouncil |
