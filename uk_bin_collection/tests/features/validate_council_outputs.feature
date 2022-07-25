Feature: Test each council output matches expected results in /outputs

    Scenario Outline: Validate Council Output
        Given the council: "<council>"
        When we scrape the data from "<council>"
        Then we should load the expected output
        And the data output from the process should match

        Examples: Councils to Test
            | council      |
            | CheshireEastCouncil |
