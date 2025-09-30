# Ecommerce search & recommendations

This repository is an example of a production setup of how to build a performant and scalable API for searching and recommending items. The intention is so sell this as SaaS to ecom customers that dont have the competence to implement superlinked themselves, and maybe have a very small team of developers and dont have time to focus on search and recommendations specifically. It should be branded as "search_rec_api" for now, and not mentioned the specific framework used (superlinked), even though the tech is not a secret.

## Server and API code

The server is developed and maintained by Superlinked, you can start it with:

```bash
python -m superlinked.server
```

And it is configured via `config.yaml`. The parameters available are described in `docs/superlinked_config.md`.

## Development plan

The plan is to utilize cloud hosting on GCP, and details can be found in `docs/development_plan.md`. We need to use Pulumi for  infrastructure as code. In general we try to use tools that we already have and not introduce new ones, unless we need some new feature, and since our team is small we like managed services and SaaS. Our current stack is:

* BigQuery
* Redis
* Postgres
* Python
* FastAPI
* Google Cloud Platform

We try to use free tiers and work within the EU region mainly. We do not maintain or develop superlinked, only the implementation code that is specific for each customer.

