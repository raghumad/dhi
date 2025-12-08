Feature: API Integration
  As a developer
  I want to ensure the FastAPI backend handles queries correctly
  So that the Frontend receives valid insights

  Scenario: Querying the Intellect
    Given the API is running at "http://localhost:8000"
    When I send a POST request to "/insight" with payload:
      """
      {
        "context": "", 
        "query": "who is sudasa"
      }
      """
    Then the response status code should be 200
    And the response should contain "output"
    And the response should contain "token_usage"
