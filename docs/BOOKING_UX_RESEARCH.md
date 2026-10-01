# Booking UX Research — 2026-09-30

## Question

Should the prototype use a booking call-to-action (CTA), and what should it promise?

## Reviewed patterns

| Reference | Observed pattern | Useful lesson |
| --- | --- | --- |
| RGL Air Conditioning contact page | Compact contact-page service form: identity, contact, aircon type, address, service selection, notes | A small local business can use one concise request form. |
| Carrier Philippines service booking | Service selection starts the flow: installation, cleaning, repair, or site survey | Ask for the type of help early to route the request. |
| Arctic Air Manila cleaning page | “Submit Booking Request” with name, phone/Viber, unit type, city | Use request wording when the business will review details before confirmation. |
| Cebu Aircon Care | Form asks for location, device type, service need, preferred date, and message | Unit/device type and preferred timing improve technician preparation. |
| Mature HVAC online schedulers | “Book” or “Schedule” is paired with live slots and automatic confirmation | Do not promise this until the prototype has real capacity/availability and authorized notifications. |

## Decision

Use a single-page **service-request** CTA, not an instant-booking promise.

- Page heading: `Request a Balik-Lamig service`.
- Primary button: `Send service request`.
- Receipt: request received and `pending_review`; staff must review coverage and preferred time before confirmation.
- Keep the form concise and use a visible three-step expectation: submit request → staff review → separate confirmation.
- Do not display “Book Now,” a live calendar, guaranteed response time, pricing, payment, real phone number, or external message link in this prototype.

## Next data improvement

Add an `aircon_type` field in a later controlled schema increment. Recommended initial choices: split type, window type, floor-standing, or not sure. This is useful for routing but is not required for the current request/validation proof.

## Sources

- https://www.rglairconditioning.com/contact-us
- https://cares.carrier.com.ph/book-service?selection=Cleaning
- https://arcticairmanila.ph/aircon-cleaning
- https://cebuairconcare.com/
- https://otheating.com/book
