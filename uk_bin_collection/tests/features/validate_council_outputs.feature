Feature: Test each council output matches expected results in /outputs

    Scenario Outline: Validate Council Output
        Given the council: "<council>"
        When we scrape the data from "<council>"
        Then the result is valid json
        And the output should validate against the schema

        Examples: Testing : <council>
            | council      |
            | BlackburnCouncil |
            | CardiffCouncil |
            | CastlepointDistrictCouncil |
            | CheshireEastCouncil |
            | CrawleyBoroughCouncil |
            | EastDevonDC |
            | HuntingdonDistrictCouncil |
            | LeedsCityCouncil |
            | MidSussexDistrictCouncil |
            | NELincs |
            | NewcastleCityCouncil |
            | SouthTynesideCouncil |
            | StHelensBC |
            | StockportBoroughCouncil |
            | TorridgeDistrictCouncil |
            | WakefieldCityCouncil |
            | WarwickDistrictCouncil |
            | WiganBoroughCouncil |
