Feature: Test each council output matches expected results

  Scenario: Validate Council Output
    Given the council
    When we scrape the data from the council
    Then the result is valid json
    And the output should validate against the schema
