# Requirements Document

## Introduction

ClinicalProof is a web application that provides verifiable AI-generated medical summaries from publicly available PubMed abstracts. The system combines natural language processing with blockchain-based verification to ensure transparency and accountability of AI-generated medical content. The application fetches medical abstracts, generates audience-specific summaries, cryptographically hashes the output, and stores proof on the Ethereum Sepolia testnet blockchain.

## Glossary

- **System**: The ClinicalProof web application
- **PubMed**: A free search engine accessing primarily the MEDLINE database of references and abstracts on life sciences and biomedical topics
- **PMID**: PubMed Identifier, a unique number assigned to each PubMed record
- **Abstract**: A brief summary of a research article available in PubMed
- **Summary**: AI-generated text derived from a PubMed abstract
- **Hash**: A SHA-256 cryptographic hash value computed from PMID, summary text, and timestamp
- **Blockchain**: The Ethereum Sepolia testnet public distributed ledger
- **Smart_Contract**: An immutable program deployed on the Ethereum blockchain that stores and verifies hashes
- **Transaction_Hash**: A unique identifier for a blockchain transaction
- **Verifier**: A user who wants to confirm that a summary was recorded on blockchain
- **Technical_Summary**: A summary preserving scientific terminology for medical professionals
- **Simplified_Summary**: A summary using plain language for general audiences
- **Bullet_Summary**: A concise list of key facts from the abstract

## Requirements

### Requirement 1: PubMed Abstract Retrieval

**User Story:** As a user, I want to retrieve medical abstracts from PubMed, so that I can generate verified summaries from legitimate public sources.

#### Acceptance Criteria

1. WHEN a user provides a PubMed URL, THE System SHALL extract the PMID from the URL
2. WHEN a valid PMID is extracted, THE System SHALL fetch the abstract via the NCBI E-utilities API
3. WHEN the abstract is successfully fetched, THE System SHALL display the raw abstract text to the user
4. IF the PMID is invalid or not found, THEN THE System SHALL return an error message indicating the PMID could not be retrieved
5. WHEN fetching from the NCBI API, THE System SHALL complete the request within 5 seconds

### Requirement 2: AI Summary Generation

**User Story:** As a medical professional or patient, I want audience-specific summaries of medical abstracts, so that I can understand research findings at an appropriate level of detail.

#### Acceptance Criteria

1. WHEN a PubMed abstract is retrieved, THE System SHALL generate a Technical_Summary preserving scientific terminology
2. WHEN a PubMed abstract is retrieved, THE System SHALL generate a Simplified_Summary using plain language
3. WHEN a PubMed abstract is retrieved, THE System SHALL generate a Bullet_Summary with key facts
4. WHEN generating summaries, THE System SHALL use medical NLP models (facebook/bart-large-cnn or microsoft/BiomedNLP-PubMedBERT)
5. WHEN displaying any summary, THE System SHALL label it as "AI-generated summary" and "Not medical advice"
6. WHEN generating all three summaries, THE System SHALL complete processing within 5 seconds

### Requirement 3: Cryptographic Hashing

**User Story:** As a system operator, I want to create unique cryptographic hashes of summaries, so that I can prove their authenticity later.

#### Acceptance Criteria

1. WHEN a summary is generated, THE System SHALL compute a SHA-256 Hash from the PMID, summary text, and timestamp
2. WHEN computing the Hash, THE System SHALL use the exact summary text without modification
3. WHEN the Hash is computed, THE System SHALL display the Hash value to the user

### Requirement 4: Blockchain Proof Storage

**User Story:** As a user, I want proof of my summary stored on blockchain, so that I can verify its authenticity independently.

#### Acceptance Criteria

1. WHEN a Hash is computed, THE System SHALL store the Hash and timestamp on the Ethereum Sepolia testnet via the Smart_Contract
2. WHEN the blockchain transaction completes, THE System SHALL return the Transaction_Hash to the user
3. WHEN the Transaction_Hash is returned, THE System SHALL provide a clickable Etherscan link to view the transaction
4. IF the blockchain transaction fails, THEN THE System SHALL return an error message indicating the storage failed
5. THE Smart_Contract SHALL be immutable after deployment

### Requirement 5: Summary Verification

**User Story:** As a Verifier, I want to confirm that a summary was recorded on blockchain, so that I can trust its authenticity.

#### Acceptance Criteria

1. WHEN a Verifier provides a PMID and summary text, THE System SHALL recompute the Hash using SHA-256
2. WHEN the Hash is recomputed, THE System SHALL call the Smart_Contract verify function with the Hash
3. IF the Hash exists in the Smart_Contract, THEN THE System SHALL display the original timestamp
4. IF the Hash does not exist in the Smart_Contract, THEN THE System SHALL indicate the summary cannot be verified
5. WHEN verification completes, THE System SHALL display the result within 3 seconds

### Requirement 6: Input Validation and Security

**User Story:** As a system administrator, I want robust input validation and security controls, so that the system operates safely and reliably.

#### Acceptance Criteria

1. WHEN a user submits a PMID, THE System SHALL validate that it contains only numeric characters
2. WHEN a user submits a PubMed URL, THE System SHALL validate that it matches the expected PubMed URL format
3. WHEN the System receives API requests, THE System SHALL enforce rate limiting to prevent abuse
4. THE System SHALL store only public abstract data and generated summaries
5. THE System SHALL reject any input containing SQL injection patterns or script tags

### Requirement 7: User Interface and Disclaimers

**User Story:** As a user, I want a clear and responsive interface with appropriate disclaimers, so that I understand the limitations of AI-generated content.

#### Acceptance Criteria

1. THE System SHALL display a disclaimer stating "AI-generated summary" on all summary outputs
2. THE System SHALL display a disclaimer stating "Not medical advice" on all summary outputs
3. THE System SHALL display a statement of limitations explaining that summaries may omit nuance
4. WHEN accessed from any device, THE System SHALL provide a mobile-responsive interface
5. WHEN displaying blockchain verification results, THE System SHALL clearly indicate whether verification succeeded or failed

### Requirement 8: Performance and Availability

**User Story:** As a user, I want fast and reliable access to the system, so that I can efficiently retrieve and verify summaries.

#### Acceptance Criteria

1. WHEN generating summaries, THE System SHALL complete all three summary types within 5 seconds
2. WHEN verifying a summary, THE System SHALL return results within 3 seconds
3. WHEN fetching from PubMed, THE System SHALL complete the request within 5 seconds
4. THE System SHALL achieve a summary generation success rate greater than 95%
5. THE System SHALL achieve a verification success rate of 100% for valid hashes

### Requirement 9: Data Privacy and Compliance

**User Story:** As a compliance officer, I want the system to handle only public data with clear limitations, so that we meet healthcare data regulations.

#### Acceptance Criteria

1. THE System SHALL process only publicly available PubMed abstracts
2. THE System SHALL store no patient-level data
3. THE System SHALL store no private clinical data
4. THE System SHALL display limitations stating "Abstract-only, no full-text parsing"
5. THE System SHALL display limitations stating "Blockchain does not validate medical correctness"

### Requirement 10: Smart Contract Functionality

**User Story:** As a developer, I want a reliable smart contract for hash storage and verification, so that blockchain proof is trustworthy and immutable.

#### Acceptance Criteria

1. THE Smart_Contract SHALL store Hash values with associated timestamps
2. WHEN queried with a Hash, THE Smart_Contract SHALL return the timestamp if the Hash exists
3. WHEN queried with a Hash that does not exist, THE Smart_Contract SHALL indicate the Hash was not found
4. THE Smart_Contract SHALL be deployed on the Ethereum Sepolia testnet
5. THE Smart_Contract SHALL remain immutable after deployment
