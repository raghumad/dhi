Feature: Search CLI Interaction
  As a user
  I want to query the search engine via a command line interface
  So that I can get answers from the scriptures

  Scenario: Basic startup and query
    Given the search engine is running
    When I search for "Who is Agni?"
    Then the output should contain "Agni"
    And I can exit the application
