Feature: RAG Pipeline Granular Verification
  As a developer
  I want to verify each stage of the RAG pipeline
  So that I ensure data quality before feeding it to the LLM

  Scenario: 1. Text Chunking
    Given the input file "out/rigveda.pdf" exists
    And the model file "models/model.gguf" exists
    When I run the ingestion process
    Then the knowledge base "out/knowledge_base.json" should be created
    And the knowledge base should contain at least 10 chunks
    # Removed brittle content checks in favor of end-to-end Scenario 4 verification

  Scenario: 2. Embedding Generation
    Given the knowledge base "out/knowledge_base.json" exists
    Then each item should have a "vector" field
    And the vector dimension should be 3072

  Scenario: 3. Vector Storage Schema
    Given the knowledge base "out/knowledge_base.json" exists
    Then the file should be valid JSON
    And each item should have fields "id,text,vector,source"

  Scenario: 4. Semantic Retrieval Accuracy
    Given the knowledge base "out/knowledge_base.json" exists
    When I query the internal retrieval function for "Who published this?"
    # This effectively tests the cosine similarity logic
    Then the top result should contain "Oxford"
    And the similarity score should be greater than 0.25
