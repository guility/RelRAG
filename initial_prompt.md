We are developing RelRAG software.
It's a framework around Postgres 18 and pgvector that enables RAG and full-text search capabilities, while preserving best properties and features of Postgres, like point-in-time recovery, ACID, scalability, etc.

It's important that every operation in API complies with ACID.

RAG uses following structure:
Embedding - one-to-one-> Chunk
Chunk - many-to-one -> Pack / Cut
Pack / Cut - many-to-one -> Document
Document - one-to-many -> Property
Pack - many-to-many -> Collection
Collection - one-to-one -> Configuration
Collection - many-to-many -> Permission

Document should have an md5 hash of a source document (as binary object).
That hash should be used for deduplication.
Every Pack / Cut should have a creation date.
Every Document might have unlimited number of key:value properties that should be stored in Property table alongside their type, which implies type of conditions we could apply to the property to filter by it.

When document is splitted in chunks in a specific manner - resulting set of chunks is called Pack / Cut.
Manner of splitting documents in chunks and embedding model used to obtain embedding vectors are properies of a collection, that might be stored as Configuration.
When somebody loads a document - he must send the target Collection id.

There must be a method to migrate collection from one Configuration to another, that includes reconstructing chunks and embeddings by a new method.

Authorization for API should rely on SSO with OIDC provider of Keycloak.
Use OpenAI compatible API for embeddings.

Use Python as a Backend language.
Pay attention to SOLID principles, espescially single-responsibility principle.
Also use ruff as a linter and uv as a package manager for python.

Make sure that we have full CRUD operations for Packs/Cuts, Documents and Collections, and that related objects are being deleted as a cascade.
Also, make sure to create both hard and soft versions of update and delete operations.