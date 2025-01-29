## Building the Docker image

From the `crystaldba/agent` directory, run:

```bash
docker build -t crystaldba-client -f ./client/Dockerfile .
```

## Running the Docker image

If you are running on Linux you can use the following command to launch the Crystal DBA client.

```bash
docker run -it --network host \
  -e CRYSTAL_API_URL=http://localhost:7080 \
  -e DATABASE_URL=<YOUR DATABASE URL> \
  crystaldba-client
```

This command assumes the server is accessible at `localhost:7080` (as described in the [server README](../server/README.md)).
If you are running the server somewhere else, you will need to set `CRYSTAL_API_URL` appropriately.

If you are running on MacOS host mode networking gets you host mode on the virtual machine that runs the Docker container, so you will need to additionally tunnel your database connection to that virtual machine.