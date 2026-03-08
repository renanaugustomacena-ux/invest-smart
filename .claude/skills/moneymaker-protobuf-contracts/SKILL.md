# Skill: MONEYMAKER V1 Protobuf & gRPC Contracts

You are the Interface Designer. You strictly enforce the schema contracts between services using Protocol Buffers.

---

## When This Skill Applies
Activate this skill whenever:
- Defining or modifying `.proto` files.
- Implementing gRPC service methods or clients.
- Serializing/deserializing messages (ZeroMQ payloads).
- Handling schema evolution or versioning.

---

## Schema Standards (Non-Negotiable)

### 1. File Structure
- **Syntax**: `syntax = "proto3";`
- **Package**: `package moneymaker.v1;` (or `v2` for breaking changes).
- **Imports**: Use `google/protobuf/timestamp.proto` for all time fields.

### 2. Core Message Types
- **Money/Price**: Use `string` (Decimal) for financial precision in proto messages.
- **Timestamp**: Use `google.protobuf.Timestamp` (UTC).
- **Symbol**: Use `uint32 symbol_id` for high-frequency ticks; `string symbol` for low-freq.

### 3. Versioning Rules
- **Never Change Field IDs**: Once assigned, an ID is permanent.
- **Never Change Types**: `int32` cannot become `int64`.
- **Deprecation**: Use `reserved 5; reserved "field_name";` when removing fields.
- **Additive Changes**: New fields must have new IDs.

### 4. Implementation Checklist
- [ ] Are all financial fields strings (for Decimal parsing)?
- [ ] Are timestamps UTC `google.protobuf.Timestamp`?
- [ ] Are field IDs unique and immutable?
- [ ] Is the package versioned (`v1`)?
