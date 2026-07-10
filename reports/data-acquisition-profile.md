# Data Acquisition Profile

## Booking Source

- Rows: `119390`
- Columns: `32`
- Required fields present: `True`
- Room type mismatch rate: `0.124943`

## Numeric Summaries

| Field | Count | Min | Mean | Median | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| lead_time | 119390 | 0.0 | 104.0114 | 69.0 | 737.0 |
| stays_in_weekend_nights | 119390 | 0.0 | 0.9276 | 1.0 | 19.0 |
| stays_in_week_nights | 119390 | 0.0 | 2.5003 | 2.0 | 50.0 |
| days_in_waiting_list | 119390 | 0.0 | 2.3211 | 0.0 | 391.0 |
| adr | 119390 | -6.38 | 101.8311 | 94.575 | 5400.0 |
| total_of_special_requests | 119390 | 0.0 | 0.5714 | 0.0 | 5.0 |
| booking_changes | 119390 | 0.0 | 0.2211 | 0.0 | 21.0 |

## Categorical Counts

### `hotel`

| Value | Count |
| --- | ---: |
| `City Hotel` | 79330 |
| `Resort Hotel` | 40060 |
### `customer_type`

| Value | Count |
| --- | ---: |
| `Transient` | 89613 |
| `Transient-Party` | 25124 |
| `Contract` | 4076 |
| `Group` | 577 |
### `is_repeated_guest`

| Value | Count |
| --- | ---: |
| `0` | 115580 |
| `1` | 3810 |
### `reserved_room_type`

| Value | Count |
| --- | ---: |
| `A` | 85994 |
| `D` | 19201 |
| `E` | 6535 |
| `F` | 2897 |
| `G` | 2094 |
| `B` | 1118 |
| `C` | 932 |
| `H` | 601 |
### `assigned_room_type`

| Value | Count |
| --- | ---: |
| `A` | 74053 |
| `D` | 25322 |
| `E` | 7806 |
| `F` | 3751 |
| `G` | 2553 |
| `C` | 2375 |
| `B` | 2163 |
| `H` | 712 |
### `market_segment`

| Value | Count |
| --- | ---: |
| `Online TA` | 56477 |
| `Offline TA/TO` | 24219 |
| `Groups` | 19811 |
| `Direct` | 12606 |
| `Corporate` | 5295 |
| `Complementary` | 743 |
| `Aviation` | 237 |
| `Undefined` | 2 |

## Notes

- `adr` can include unusual values in this public dataset; downstream transforms should flag rather than silently drop them.
- `room_type_mismatch` is derived from reserved vs assigned room type and is a useful service-friction proxy, not proof of a service failure.
- The booking source has no compensation labels.
