# TryItOn Python SDK — AI Virtual Try-On API

Official Python client for the [TryItOn](https://tryiton.now) virtual try-on API. Add photoreal AI virtual try-on for clothing, accessories, hairstyles, and tattoos to your Python application with a few lines of code.

- Virtual clothing try-on and accessory try-on (eyewear, footwear, headwear, jewelry)
- Hairstyle and tattoo try-on
- Type-hinted client with a built-in job polling helper

Full API reference: [docs.tryiton.now](https://docs.tryiton.now) · Get an API key: [tryiton.now/app/developer](https://tryiton.now/app/developer)

## Installation

```bash
pip install tryiton
```

Requires Python 3.8 or later.

## Quickstart: run a virtual try-on

Submit a garment and a model photo, then wait for the generated result image.

```python
import os
from tryiton import TryItOn

client = TryItOn(api_key=os.environ["TRYITON_API_KEY"])

# Submit a clothing try-on
job_id = client.try_on_fashion(
    model_image="https://example.com/model.jpg",
    garment_image="https://example.com/tshirt.jpg",
    category="clothing",
    subcategory="tops",
)

# Poll until the job completes and return the output image URL(s)
urls = client.wait_for_result(job_id)
print(urls[0])  # CDN URL, available for 72 hours
```

Image inputs accept a public URL or a base64 data URL (`data:image/png;base64,...`).

## Core parameters

`try_on_fashion` covers clothing and accessory try-on. The most important parameters:

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| `model_image` | str | Yes | URL or base64 data URL of the person. |
| `garment_image` | str | Yes | URL or base64 data URL of the garment or accessory. |
| `category` | str | No | Item type: `auto`, `clothing`, `eyewear`, `footwear`, `headwear`, `jewelry`, `accessories`, or `others`. `auto` detects it for you. |
| `subcategory` | str | No | Required for `clothing` (`tops`, `bottoms`, `dresses`), `jewelry`, and `accessories`. |

Additional options (`mode` and `moderation_level` for clothing; `num_samples` 1–4 and `output_format` `png`/`jpeg` for every try-on, including hairstyle and tattoo) are documented in the [API reference](https://docs.tryiton.now).

## Other endpoints

```python
# Hairstyle try-on (see tryiton.HAIRCUTS for all supported values)
client.try_on_hairstyle(face_image=face_url, haircut="BuzzCut", hair_color="ash blonde")

# Tattoo try-on — place it with free text...
client.try_on_tattoo(body_image=body_url, design_image=design_url, placement="on the right forearm, small")
# ...or pin the exact spot with a region box (normalized 0-1, from the image's top-left)
client.try_on_tattoo(body_image=body_url, design_image=design_url, region={"x": 0.32, "y": 0.18, "w": 0.28, "h": 0.34})

# Poll a job manually, or check your credit balance
status = client.get_status(job_id)   # Status(status, output, error)
credits = client.get_credits()        # Credits(on_demand, subscription, purchased, reserved)
```

## Live try-on (real-time webcam)

Your server prepares garments and starts sessions with the API key. The shopper's browser streams with the
[`tryiton-live`](https://www.npmjs.com/package/tryiton-live) npm package, using only the session-scoped response.

```python
# Once per product, e.g. at catalog sync (cached per image + category):
garment = client.prepare_live_garment(product_image_url, category="clothing", subcategory="tops")

# When a shopper opens live try-on. Return `start` to the browser as-is (e.g. as JSON):
start = client.start_live_session(
    garment_id=garment["id"],
    end_user_id=shopper_id,                     # one stream per end user
    allowed_origin="https://shop.example.com",  # locks the media token to your site
)

client.get_live_session(start["session"]["id"])   # {"status", "seconds", "creditsCharged", ...}
client.stop_live_session(start["session"]["id"])  # end it from your server
client.get_live_config()                          # {"enabled", "secondsPerCredit", "maxSeconds", ...}
```

Billing is per `secondsPerCredit` seconds of streamed video, from the first try-on frame. Garment switches during a
session are free.

`prepare_live_garment` also takes optional overrides:

```python
client.prepare_live_garment(
    product_image_url,
    category="footwear",
    detail_images=[side_view_url, back_view_url],           # up to 3 extra views; they only sharpen the description
    description="black leather knee-high boots",            # your description (max 200), used in the generated prompt
    instructions="Replace only the shoes with the boots.",  # or your own prompt (max 1000), used verbatim
    enhance_prompt=False,                                   # keep the prompt as-is (default True)
)
```

### Outfits

Combine 2-3 prepared garments into one outfit worn together. The outfit's `id` works wherever a garment id does
(`start_live_session`, the browser's `switchGarment`). To swap one item, prepare the new combination (cached) and
switch to it.

```python
top = client.prepare_live_garment(shirt_url, category="clothing", subcategory="tops")
trousers = client.prepare_live_garment(trousers_url, category="clothing", subcategory="bottoms")
shoes = client.prepare_live_garment(shoes_url, category="footwear")

outfit = client.prepare_live_outfit([top["id"], trousers["id"], shoes["id"]])
# outfit["category"] == "outfit", outfit["items"] = the garment ids top to bottom
start = client.start_live_session(garment_id=outfit["id"], end_user_id=shopper_id)

# Later the shopper picks another top: prepare that outfit and switch the running stream to it.
jacket = client.prepare_live_garment(jacket_url, category="clothing", subcategory="tops")
next_outfit = client.prepare_live_outfit([jacket["id"], trousers["id"], shoes["id"]])
# Send next_outfit["id"] to the browser, which calls live.switchGarment(id) (tryiton-live).
```

`prepare_live_outfit` also takes `instructions` and `enhance_prompt`, as above.

## Error handling

All failures raise `TryItOnError`, which carries the HTTP status code and the API error name.

```python
from tryiton import TryItOn, TryItOnError

try:
    client.try_on_fashion(...)
except TryItOnError as err:
    print(err.status, err.error_name, str(err))  # e.g. 429, "OutOfCredits"
```

## Typing

The package ships `py.typed`. `get_status` and `get_credits` return the `Status` and `Credits` dataclasses. The live
methods return plain dicts typed as `TypedDict`s (`LiveConfig`, `LiveGarment`, `LiveSession`, `LiveSessionStart`),
all importable from `tryiton`.

## Notes

- Output image URLs expire 72 hours after completion. Download any results you want to keep.
- Failed jobs are never charged.

## Development

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                 # unit tests + the shared contract cases
python -m mypy tryiton # strict type check
```

`tests/fixtures/sdk-cases.json` holds the request/response cases every TryItOn SDK runs. It is generated: edit the
source in the backend repo (`api-contract/sdk-cases.json`) and re-sync, never the copy here. Changes are listed in
[CHANGELOG.md](CHANGELOG.md).

## Documentation

Full documentation, parameter reference, and guides: [docs.tryiton.now](https://docs.tryiton.now)

## License

MIT
