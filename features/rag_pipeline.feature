Feature: RAG Pipeline Granular Verification
  As a developer
  I want to verify each stage of the RAG pipeline
  So that I ensure data quality before feeding it to the LLM

  Scenario: 1. Text Chunking & Indexing
    Given the input file "out/rigveda.pdf" exists
    And the model file "models/llama-3.2-3b-instruct-q4km.gguf" exists
    When I force run the ingestion process
    Then the binary index "out/rigveda.hnsw" should be created
    And the binary metadata "out/rigveda.bin" should be created
    And the text blob "out/rigveda.txt" should be created

  Scenario: 2. Embedding Index Properties
    Given the binary index "out/rigveda.hnsw" exists
    Then the file size should be greater than 1000

  Scenario: 3. Vector Storage Schema
    Given the binary metadata "out/rigveda.bin" exists
    Then the file header should contain magic bytes "DHIM"

  Scenario: 4. Semantic Retrieval Accuracy
    Given the binary index "out/rigveda.hnsw" exists
    When I query the internal retrieval function for "Who published this?"
    Then the top result should contain "Oxford"
    And the similarity score should be greater than 0.25

  Scenario: 5. Idempotency Verification
    Given the binary index "out/rigveda.hnsw" exists
    When I run the ingestion process
    Then the ingestion output should contain "Artifacts exist"
    And the ingestion output should contain "Skipping ingestion"
