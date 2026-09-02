# EDI 835 Parser Backlog

This backlog tracks known cases where valid EDI 835 data is parsed but omitted,
filtered, overwritten, transformed incorrectly, or never captured in the JSON
projection. Priorities reflect the risk of silently losing source data.

## Definition of done

Every item below should meet these requirements:

- Preserve every supported occurrence in source order.
- Preserve explicit zero and empty values without using truthiness as a filter.
- Preserve the raw X12 code when also exposing a friendly description.
- Do not replace source values with hardcoded placeholders when the source value
  is available.
- Add focused unit tests and at least one representative end-to-end fixture test.
- Confirm that JSON and database persistence retain the same information.

## Recently addressed

- [x] Emit every claim-level NM1 entity instead of selecting only the `QC`
  patient. Regression coverage includes `82`, `74`, `IL`, `PR`, `QC`, and `TT`.

## P0: Parsed data omitted from JSON

### Claim-level REF segments

- [ ] Replace the hardcoded claim `"REF": []` value with serialization of every
  entry in `Claim.references`.
- [ ] Preserve the reference qualifier and value without limiting qualifier
  codes.
- [ ] Test multiple REF segments on one claim.

### Claim-level AMT segments

- [ ] Change the claim model from a single `amount` value to an ordered
  collection so later AMT segments do not overwrite earlier ones.
- [ ] Replace the hardcoded claim `"AMT": []` value with serialization of every
  parsed AMT segment.
- [ ] Repair or replace `_get_claim_amt_data()`, which currently references the
  nonexistent `self.amounts` attribute and is not called.
- [ ] Test multiple qualifiers and an explicit zero amount.

### Service-level REF segments

- [ ] Replace the hardcoded service `"REF": []` value with serialization of
  every entry in `Service.references`.
- [ ] Test multiple service references and unmapped qualifier codes.

### Service-level LQ remarks

- [ ] Add all parsed `Service.remarks` entries to the service JSON output.
- [ ] Preserve both the raw remark qualifier and remark code.
- [ ] Test multiple LQ segments on one service line.

### Service-level AMT segments

- [ ] Change the service model from a single `amount` value to an ordered
  collection so later AMT segments do not overwrite earlier ones.
- [ ] Emit every AMT qualifier rather than selecting only `B6` through
  `allowed_amount`.
- [ ] Ensure an explicit zero monetary amount is emitted.
- [ ] Retain `allowed_amount` as a convenience property without using it as the
  JSON source of truth.

### Service-level NM1 segments

- [ ] Teach the service loop to capture NM1 segments instead of warning and
  discarding them.
- [ ] Emit all service-level NM1 entries in source order with no NM101 filter.
- [ ] Persist service-level NM1 entries consistently in both database seed paths.

## P0: Incorrect or fabricated transaction values

### BPR transaction handling code

- [ ] Parse BPR01 separately and use it for `transaction_handling_code`.
  The current projection emits the segment identifier `"BPR"` instead.
- [ ] Add a regression test covering common BPR01 values.

### ST and SE control data

- [ ] Parse ST01 and ST02 rather than emitting hardcoded `"835"` and `"1234"`.
- [ ] Parse SE01 and SE02 rather than emitting hardcoded `"33"` and `"1234"`.
- [ ] Validate matching ST02/SE02 control numbers without dropping either value.

### Envelope data

- [ ] Parse and emit GS, GE, and IEA instead of returning `null`.
- [ ] Preserve envelope control numbers and transaction/group counts.
- [ ] Add multi-transaction envelope tests.

## P1: Segment fields not captured

### NM1 elements after NM109

- [ ] Parse NM110 through NM112 when present.
- [ ] Replace the hardcoded empty relationship and secondary-identification
  fields in NM1 JSON with the parsed values.
- [ ] Test short NM1 segments and fully populated NM1 segments.

### CLP fields

- [ ] Parse CLP05 patient responsibility instead of always emitting an empty
  string.
- [ ] Parse the remaining supported CLP elements currently represented by empty
  JSON fields, including facility type, claim frequency, patient status, DRG,
  DRG weight, and discharge fraction.
- [ ] Use safe optional-element access so shorter valid segments continue to
  parse.

### SVC fields

- [ ] Parse SVC04 revenue code instead of emitting an empty string.
- [ ] Audit and capture the remaining SVC elements that are currently skipped.
- [ ] Remove the hardcoded `adjudicated_date` placeholder or populate it from the
  correct source when available.

### BPR fields

- [ ] Parse all BPR elements represented by hardcoded empty values in JSON.
- [ ] Stop hardcoding the credit/debit flag to `"C"`; use the source element.
- [ ] Preserve account and routing identifiers as strings so leading zeros are
  not lost.
- [ ] Support optional BPR layouts safely rather than indexing required positions
  unconditionally.

### N1 organization fields

- [ ] Capture and emit N103 identification-code qualifier.
- [ ] Preserve N104 identification code as text; do not convert numeric values to
  integers and remove leading zeros.
- [ ] Preserve the raw N101 entity identifier alongside any friendly mapping.

### N3 address fields

- [ ] Parse and emit N302 address line 2.

### N4 location fields

- [ ] Parse and emit country code, location qualifier, and location identifier.
- [ ] Use safe optional-element access for partially populated N4 segments.

### Organization PER and REF segments

- [ ] Teach the organization loop to retain PER contact segments.
- [ ] Emit parsed PER data instead of always returning `null`.
- [ ] Teach the organization loop to retain organization-level REF segments.
- [ ] Support all valid occurrences in source order.

### Transaction-level DTM and REF segments

- [ ] Capture and emit transaction-level DTM segments instead of returning an
  empty list.
- [ ] Capture and emit transaction-level REF segments rather than silently
  discarding them.

## P1: Cardinality and overwrite risks

- [ ] Audit every loop attribute modeled as a scalar and confirm whether the 835
  guide permits repetition.
- [ ] Convert repeatable scalar attributes to ordered collections.
- [ ] Add duplicate-occurrence tests to prove that later segments do not silently
  overwrite earlier segments.

Known scalar overwrite risks include claim AMT, service AMT, organization N3,
and organization N4.

## P1: Database projection gaps

- [ ] Add dedicated NM1 storage for the entity identifier code so `QC`, `IL`,
  `82`, and other roles can be queried without inspecting `json_nm1`.
- [ ] Persist NM1 prefix, suffix, relationship, and secondary-identification
  values in dedicated columns where required.
- [ ] Align the regular and bulk seed paths so they persist the same claim- and
  service-level child segments.
- [ ] Add database integration tests comparing serialized JSON with inserted
  rows.

## P2: Unsupported-segment visibility

- [ ] Replace silent transaction-level and organization-level discards with
  structured warnings that include the segment identifier and loop context.
- [ ] Make warning behavior consistent across transaction, organization, claim,
  and service loops.
- [ ] Add an optional strict mode that fails on unsupported segments.
- [ ] Add a parse report listing every ignored segment and count by identifier.

## P2: Raw-code preservation

- [ ] Preserve raw entity, qualifier, status, and type codes separately from
  friendly descriptions.
- [ ] Ensure JSON fields named `*_code` contain the raw X12 code or introduce an
  explicit, documented raw/description pair.
- [ ] Test unknown codes to ensure they remain available instead of becoming
  empty or being discarded.

## Primary implementation areas

- `core/parser_extension.py`: JSON projection and most hardcoded placeholders.
- `edi_835_parser/transaction_set/transaction_set.py`: transaction-level capture,
  envelopes, and unsupported-segment handling.
- `edi_835_parser/loops/claim.py`: claim child-segment cardinality.
- `edi_835_parser/loops/service.py`: service child-segment capture and cardinality.
- `edi_835_parser/loops/organization.py`: PER/REF capture and organization child
  handling.
- `edi_835_parser/segments/`: individual element completeness.
- `db/models.py`, `db/seed.py`, and `db/seed_bulk.py`: persistence parity.
