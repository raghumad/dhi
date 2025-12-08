Feature: RAG Pipeline Granular Verification
  As a developer
  I want to verify each stage of the RAG pipeline
  So that I ensure data quality before feeding it to the LLM

  Background:
    Given the input file "out/rigveda.pdf" exists
    And the model file "models/model.gguf" exists

  Scenario: 1. Text Chunking
    When I run the ingestion process
    Then the output should be saved to "out/knowledge_base.json"
    And the knowledge base should contain at least 10 chunks
    # Check for meaningful chunking (not just characters)
    And a random chunk should be longer than 20 characters
    And a random chunk should contain "Rigveda"
  Scenario: 2. Embedding Generation
    Given the knowledge base "out/knowledge_base.json" exists
    Then every chunk should have a "vector" field
    And the embedding vector dimension should be 3072
    # 3072 is standard for Llama-3.2-3B or 4096 depending on layer? 
    # We'll allow a range or update this after first run.
    # Actually Llama 3.2 3B dimension is 3072.

  Scenario: 3. Vector Storage Schema
    Given the knowledge base "out/knowledge_base.json" exists
    Then the storage format should be valid JSON
    And each item should have fields:
      | field |
      | id    |
      | text  |
      | vector|
      | source|

  Scenario: 4. Semantic Retrieval Accuracy
    Given the knowledge base "out/knowledge_base.json" exists
    When I query the internal retrieval function for "God of Fire"
    # This effectively tests the cosine similarity logic
    Then the top result should contain "Agni"
    And the similarity score should be greater than 0.25
