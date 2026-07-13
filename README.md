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
job_id = client.try_on_clothes(
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

`try_on_clothes` covers clothing and accessory try-on. The most important parameters:

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

## Error handling

All failures raise `TryItOnError`, which carries the HTTP status code and the API error name.

```python
from tryiton import TryItOn, TryItOnError

try:
    client.try_on_clothes(...)
except TryItOnError as err:
    print(err.status, err.error_name, str(err))  # e.g. 429, "OutOfCredits"
```

## Notes

- Output image URLs expire 72 hours after completion. Download any results you want to keep.
- Failed jobs are never charged.

## Documentation

Full documentation, parameter reference, and guides: [docs.tryiton.now](https://docs.tryiton.now)

## License

MIT
