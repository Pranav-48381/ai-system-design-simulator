"""System Design Interview Simulator - Data Model Design Schemas.

Defines Pydantic schemas for candidate database schema proposals, table/collection definitions,
column attributes, indexes, partitioning/sharding strategies, and inter-table relationships.
"""

from enum import StrEnum
from typing import Any
import uuid
from pydantic import Field

from app.schemas import BaseSchema


class DatabaseParadigmEnum(StrEnum):
    """Database technology paradigms used in distributed system architectures."""

    RELATIONAL = "relational"
    DOCUMENT = "document"
    KEY_VALUE = "key_value"
    WIDE_COLUMN = "wide_column"
    GRAPH = "graph"
    TIME_SERIES = "time_series"


class RelationTypeEnum(StrEnum):
    """Cardinality and relationship type between data model entities."""

    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


class OnDeleteActionEnum(StrEnum):
    """Referential integrity trigger action on parent record deletion."""

    CASCADE = "CASCADE"
    SET_NULL = "SET NULL"
    RESTRICT = "RESTRICT"
    NO_ACTION = "NO ACTION"


class IndexTypeEnum(StrEnum):
    """Indexing structure applied for query performance optimization."""

    PRIMARY = "primary"
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"
    GIST = "gist"
    UNIQUE = "unique"
    COMPOSITE = "composite"


class ColumnSchemaDesign(BaseSchema):
    """Field or column specification within a database table or document."""

    name: str = Field(
        ...,
        description="Name of the column or attribute.",
        examples=["id", "user_id", "created_at"],
    )
    data_type: str = Field(
        ...,
        description="Data type with optional precision.",
        examples=["UUID", "VARCHAR(255)", "BIGINT", "TIMESTAMPTZ"],
    )
    is_primary_key: bool = Field(
        default=False,
        description="True if column is part of the primary key.",
    )
    is_nullable: bool = Field(
        default=False,
        description="True if null values are permitted.",
    )
    is_unique: bool = Field(
        default=False,
        description="True if unique constraint is enforced.",
    )
    default_value: str | None = Field(
        default=None,
        description="Default expression or literal value.",
        examples=["gen_random_uuid()", "NOW()"],
    )
    description: str | None = Field(
        default=None,
        description="Explanation of column semantics and data stored.",
    )


class IndexSchemaDesign(BaseSchema):
    """Index definition configured for table query acceleration."""

    name: str = Field(
        ...,
        description="Identifier name of the index.",
        examples=["idx_messages_conversation_id_created_at"],
    )
    columns: list[str] = Field(
        ...,
        description="Ordered list of columns comprising the index.",
        examples=[["conversation_id", "created_at"]],
    )
    index_type: IndexTypeEnum = Field(
        default=IndexTypeEnum.BTREE,
        description="Underlying indexing data structure.",
        examples=[IndexTypeEnum.BTREE],
    )
    is_unique: bool = Field(
        default=False,
        description="Whether index enforces uniqueness across indexed columns.",
    )
    predicate: str | None = Field(
        default=None,
        description="WHERE clause condition for partial indexes.",
        examples=["WHERE is_deleted = FALSE"],
    )


class PartitioningStrategySchema(BaseSchema):
    """Horizontal sharding or table partitioning specification."""

    is_partitioned: bool = Field(
        default=False,
        description="True if table is partitioned or sharded.",
    )
    partition_key: str | None = Field(
        default=None,
        description="Column or expression used as the partition key.",
        examples=["user_id", "created_at"],
    )
    strategy: str | None = Field(
        default=None,
        description="Partitioning methodology (RANGE, HASH, LIST, Consistent Hashing).",
        examples=["Consistent Hashing by hash(user_id)"],
    )
    num_shards: int | None = Field(
        default=None,
        ge=1,
        description="Number of physical shards or partitions.",
        examples=[64],
    )


class TableSchemaDesign(BaseSchema):
    """Comprehensive design schema for an individual table or collection."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Unique identifier for the table design.",
        examples=["tbl-url-mappings"],
    )
    name: str = Field(
        ...,
        description="Table or collection name.",
        examples=["url_mappings"],
    )
    storage_engine: str = Field(
        default="PostgreSQL 16",
        description="Target database engine or persistence tier.",
        examples=["PostgreSQL 16", "Cassandra", "MongoDB", "DynamoDB"],
    )
    paradigm: DatabaseParadigmEnum = Field(
        default=DatabaseParadigmEnum.RELATIONAL,
        description="Database classification model.",
        examples=[DatabaseParadigmEnum.RELATIONAL],
    )
    description: str | None = Field(
        default=None,
        description="Purpose and lifecycle notes for the table.",
    )
    columns: list[ColumnSchemaDesign] = Field(
        default_factory=list,
        description="Attributes and columns defined on the table.",
    )
    indexes: list[IndexSchemaDesign] = Field(
        default_factory=list,
        description="Secondary indexes defined on the table.",
    )
    partitioning: PartitioningStrategySchema | None = Field(
        default=None,
        description="Sharding or partitioning configurations.",
    )
    estimated_row_size_bytes: int | None = Field(
        default=None,
        ge=1,
        description="Estimated average byte size per row/record.",
        examples=[512],
    )
    estimated_row_count: int | None = Field(
        default=None,
        ge=0,
        description="Estimated total records stored at target scale.",
        examples=[1000000000],
    )


class RelationSchema(BaseSchema):
    """Foreign key or referential relationship between two entities."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Unique identifier for the relationship.",
        examples=["rel-messages-users"],
    )
    source_table: str = Field(
        ...,
        description="Source child table containing the foreign key.",
        examples=["messages"],
    )
    source_column: str = Field(
        ...,
        description="Source column containing foreign reference.",
        examples=["sender_id"],
    )
    target_table: str = Field(
        ...,
        description="Target parent table referenced.",
        examples=["users"],
    )
    target_column: str = Field(
        ...,
        description="Target column referenced in parent table.",
        examples=["id"],
    )
    relation_type: RelationTypeEnum = Field(
        default=RelationTypeEnum.ONE_TO_MANY,
        description="Cardinality between source and target.",
        examples=[RelationTypeEnum.ONE_TO_MANY],
    )
    on_delete: OnDeleteActionEnum = Field(
        default=OnDeleteActionEnum.CASCADE,
        description="Cascade rule on parent deletion.",
        examples=[OnDeleteActionEnum.CASCADE],
    )
    description: str | None = Field(
        default=None,
        description="Context or business integrity rule regarding this relationship.",
    )


class DataModelDesignSubmissionSchema(BaseSchema):
    """Holistic data persistence design submitted during component deep dive."""

    session_id: uuid.UUID = Field(
        ...,
        description="Associated interview session UUID.",
    )
    tables: list[TableSchemaDesign] = Field(
        default_factory=list,
        description="List of database tables/collections defined.",
    )
    relations: list[RelationSchema] = Field(
        default_factory=list,
        description="List of relationships and foreign key constraints.",
    )
    denormalization_strategy: str | None = Field(
        default=None,
        description="Explanation of intentional denormalization for read efficiency.",
    )
    caching_strategy: str | None = Field(
        default=None,
        description="Cache invalidation and write-through/cache-aside architecture.",
        examples=["Write-around cache with Redis cluster, TTL 24 hours."],
    )
    notes: str | None = Field(
        default=None,
        description="Candidate notes on consistency models (ACID vs BASE).",
    )
