![Build Status](https://github.com/crystaldba/crystaldba/actions/workflows/build.yml/badge.svg)

# 🤖 Crystal DBA for PostgreSQL 🐘

Crystal DBA is an AI teammate for PostgreSQL database administration.
We aim to ensure that everyone who runs PostgreSQL has access to a AI-powered database expertise at all times.

**Quick install**

```bash
# Using pipx (recommended)
pipx install crystaldba

# Using Docker
docker pull crystaldba/agent:latest
docker run -it --rm crystaldba/agent
```

**Useful links**

- [Installation instructions](https://www.crystaldba.ai/docs/installation)
- [Getting started guide](https://www.crystaldba.ai/docs/getting-started)
- [Full documentation](https://www.crystaldba.ai/docs/)
- [FAQ](https://www.crystaldba.ai/docs/frequently-asked-questions)

## 💡 Motivation

We all want our production PostgreSQL databases to run well—they should be reliable, performant, efficient, scalable, and secure.
If your team is fully staffed with database administrators, then you are in luck.
If not, you may find yourself working reactively, dealing with problems as they arise and looking up what to do as you go.

Oftentimes, operational responsibility for databases falls to software engineers and site reliability engineers, who usually have many other things to do.
They have better ways to spend their time than tuning or troubleshooting databases.

Reliability and security are the top priorities for database operations.
We focus on these first, to provide a solid foundation for delivering trustworthy suggestions for performance and efficiency.
Crystal DBA is designed to give you advice on how to improve your database, but it will not take actions automatically without your review and consent.

## 🧑‍💻 About the Authors

Crystal DBA is developed by the engineers and database experts at [Crystal DBA](https://www.crystaldba.ai/).
Our mission is to make it easy for you to run your database well, so you can focus on building better software.
Crystal DBA also offers commercial support for Crystal DBA and PostgreSQL.

## 📖 Frequently Asked Questions

### What is Crystal DBA?

Crystal DBA is an AI agent for operating PostgreSQL databases.
This means that it connects to an existing PostgreSQL database and takes actions, as necessary, to ensure that the database remains reliable, efficient, scalable, and secure.

### Will Crystal DBA replace my DBA?

Time will tell whether AI agents completely replace human database administrators (DBAs).
Our work suggests that AI agents will do some tasks much better than humans.
They can find patterns across large amounts of data, they are always available, and they respond instantly.
They can also draw upon extensive knowledge bases and operational datasets, allowing them to proceed with less trial and error than people.

On the other hand, people working in the team will have a more nuanced understanding of the needs of the business.
They will be better able to make high-level design decisions and to analyze trade-offs that impact the development process.

### Do I still need to hire a DBA if I use Crystal DBA?

If you do not already have a DBA on staff, then chances are good that Crystal DBA can allow you to postpone hiring one, particularly if you have platform engineers or site reliability engineers who are interested in applying its recommendations.
Crystal DBA and others also offer commercial support for PostgreSQL.

### Which PostgreSQL versions are supported?

Currently, Crystal DBA is compatible with PostgreSQL versions 13 through 17.

### Can I use Crystal DBA with my on-premises PostgreSQL installation?

At present, Crystal DBA only works with AWS RDS PostgreSQL.
Support for on-premises installations, Google Cloud SQL, and Azure SQL is coming.
We want Crystal DBA to run anywhere that PostgreSQL runs.

### Will Crystal DBA support databases other than PostgreSQL?

At present, we are fully focused on Crystal DBA for PostgreSQL.
We expect to maintain that focus for the foreseeable future.

### Is Crystal DBA open source?

We believe that every PostgreSQL database should be managed by an AI agent.
In pursuit of this vision, we are releasing the core operational features of Crystal DBA under the Apache 2.0 open source license.

For avoidance of doubt, Crystal DBA is commercial open source software.
Certain enterprise features will be available only in commercial versions of the product.

As of this writing (August 2024), there is active debate what the term “open source” means for AI models.
Is a model open if the developer releases the weights but not the training data and methods?

We are committed to providing open weights and some training data.
However, we also expect to release models trained on proprietary data sets.

### How can I get support for Crystal DBA?

Crystal DBA offers commercial support for Crystal DBA and PostgreSQL.
For more information or to discuss your needs, please contact us at [support@crystaldba.ai](mailto:support@crystaldba.ai).

### How can I support the Crystal DBA project?

Foremost, use Crystal DBA and give us feedback!

We also welcome feature suggestions, bug reports, or contributions to the codebase.
