# Property Context Profile

This layer turns public property context into comp-suitability modifiers.

It is not internal hotel inventory, margin, staffing, occupancy, comp-policy, or guest-record data.

## Target Property Context

- Property: `Santa Monica Proper Hotel`
- Public room-count signal: `262`
- Rooftop/F&B context: `true`
- Spa/wellness context: `true`
- Pool/rooftop context: `true`
- Brand-experience weight: `0.92`

## Coverage

- Competitive-set properties: `4`
- Source family: `public_property_context`
- Provenance: `observed_public_property_context`

## Decision Use

- Strengthen comp options that fit the public property experience.
- Penalize options that do not fit the property context.
- Preserve public-safety boundaries by keeping all true cost, inventory, and policy fields out of this layer.
